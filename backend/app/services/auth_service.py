from datetime import datetime, timedelta, timezone

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.security.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.security.fail2ban import RedisFail2Ban
from app.services.audit_service import log_audit

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
    fail2ban: RedisFail2Ban | None,
    request: Request | None = None,
    totp_code: str | None = None,
) -> dict:
    from app.security.middleware import get_client_ip

    client_ip = get_client_ip(request) if request else "unknown"

    if fail2ban and await fail2ban.is_banned(client_ip):
        raise PermissionError("IP temporarily banned due to too many failed attempts")

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        if fail2ban:
            await fail2ban.record_attempt(client_ip)
            await fail2ban.check_and_ban(client_ip)
        raise ValueError("Invalid credentials")

    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        raise PermissionError("Account locked, try again later")

    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            user.failed_login_count = 0
        await db.commit()

        if fail2ban:
            await fail2ban.record_attempt(client_ip)
            await fail2ban.check_and_ban(client_ip)

        await log_audit(db, None, "auth.login_failed", details={"username": username}, request=request)
        await db.commit()
        raise ValueError("Invalid credentials")

    # TOTP verification if enabled
    if user.totp_enabled:
        if not totp_code:
            raise ValueError("TOTP code required")
        from app.security.totp import verify_totp
        if not verify_totp(user.totp_secret, totp_code):
            user.failed_login_count += 1
            await db.commit()
            raise ValueError("Invalid TOTP code")

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    await db.commit()

    if fail2ban:
        await fail2ban.clear(client_ip)

    await log_audit(db, user.id, "auth.login", request=request)
    await db.commit()

    access_token = create_access_token(user.id, user.username)
    refresh_token = create_refresh_token(user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def refresh_access_token(
    db: AsyncSession, refresh_token_str: str, token_blacklist=None,
) -> dict:
    try:
        payload = decode_token(refresh_token_str)
    except Exception:
        raise ValueError("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise ValueError("Invalid token type")

    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise ValueError("Invalid token payload")

    old_jti = payload.get("jti")
    old_exp = payload.get("exp", 0)

    # Check if this refresh token was already revoked (replay detection)
    if token_blacklist and old_jti:
        if await token_blacklist.is_revoked(old_jti):
            # Possible token theft — revoke ALL tokens for this user
            await token_blacklist.revoke_all_for_user(user_id)
            raise ValueError("Refresh token reuse detected, all sessions revoked")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise ValueError("User not found or inactive")

    # Revoke the old refresh token so it can't be reused
    if token_blacklist and old_jti:
        import time
        ttl = max(int(old_exp - time.time()), 0)
        if ttl > 0:
            await token_blacklist.revoke(old_jti, ttl)

    access_token = create_access_token(user.id, user.username)
    new_refresh_token = create_refresh_token(user.id)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def change_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
    request: Request | None = None,
):
    if not verify_password(current_password, user.password_hash):
        raise ValueError("Current password is incorrect")

    user.password_hash = hash_password(new_password)
    await db.commit()

    await log_audit(db, user.id, "auth.password_change", request=request)
    await db.commit()
