import time

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    TokenResponse,
    UserResponse,
)
from app.security.auth import decode_token
from app.services.auth_service import authenticate_user, change_password, refresh_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)
security = HTTPBearer(auto_error=False)

_is_local = settings.PANEL_DOMAIN in ("localhost", "127.0.0.1", "")
COOKIE_SECURE = not _is_local
COOKIE_SAMESITE = "lax"
COOKIE_DOMAIN = None  # Let the browser infer from the request


def _set_token_cookies(response: Response, access_token: str, refresh_token: str):
    """Set tokens as HttpOnly cookies instead of returning them in body."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/api",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        path="/api/v1/auth",
    )


def _clear_token_cookies(response: Response):
    response.delete_cookie("access_token", path="/api")
    response.delete_cookie("refresh_token", path="/api/v1/auth")


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, response: Response, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    fail2ban = getattr(request.app.state, "fail2ban", None)
    try:
        result = await authenticate_user(db, body.username, body.password, fail2ban, request)
    except PermissionError as e:
        raise HTTPException(status_code=423, detail=str(e))
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    _set_token_cookies(response, result["access_token"], result["refresh_token"])

    return {
        "message": "Login successful",
        "expires_in": result["expires_in"],
    }


@router.post("/refresh")
@limiter.limit("10/minute")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(default=None),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    blacklist = getattr(request.app.state, "token_blacklist", None)
    try:
        result = await refresh_access_token(db, refresh_token, blacklist)
    except ValueError as e:
        _clear_token_cookies(response)
        raise HTTPException(status_code=401, detail=str(e))

    _set_token_cookies(response, result["access_token"], result["refresh_token"])

    return {
        "message": "Token refreshed",
        "expires_in": result["expires_in"],
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    access_token: str | None = Cookie(default=None),
):
    """Revoke the current access token and clear cookies."""
    blacklist = getattr(request.app.state, "token_blacklist", None)

    if blacklist and access_token:
        try:
            payload = decode_token(access_token)
            jti = payload.get("jti")
            exp = payload.get("exp", 0)
            if jti:
                ttl = max(int(exp - time.time()), 0)
                if ttl > 0:
                    await blacklist.revoke(jti, ttl)
        except Exception:
            pass

    _clear_token_cookies(response)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user


@router.put("/password")
@limiter.limit("3/minute")
async def update_password(
    request: Request,
    body: PasswordChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await change_password(db, user, body.current_password, body.new_password, request)
        return {"message": "Password updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
