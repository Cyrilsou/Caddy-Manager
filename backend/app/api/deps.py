from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.security.auth import decode_token
from app.security.middleware import get_client_ip

# Accept Bearer header (backward compat / API clients) but don't require it
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    access_token_cookie: str | None = Cookie(default=None, alias="access_token"),
    db: AsyncSession = Depends(get_db),
) -> User:
    # Try Bearer header first, then HttpOnly cookie
    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    elif access_token_cookie:
        token = access_token_cookie

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    jti = payload.get("jti")
    iat = payload.get("iat", 0)
    if isinstance(iat, float):
        iat = int(iat)

    blacklist = getattr(request.app.state, "token_blacklist", None)
    if blacklist and jti:
        if await blacklist.is_revoked(jti):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
        if await blacklist.is_user_revoked_before(user_id, iat):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user


def get_request_ip(request: Request) -> str:
    return get_client_ip(request)
