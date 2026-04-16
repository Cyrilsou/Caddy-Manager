from fastapi import APIRouter, Depends, HTTPException, Request
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
    RefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.security.auth import decode_token
from app.services.auth_service import authenticate_user, change_password, refresh_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)
security = HTTPBearer()


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    fail2ban = getattr(request.app.state, "fail2ban", None)
    try:
        result = await authenticate_user(db, body.username, body.password, fail2ban, request)
        return result
    except PermissionError as e:
        raise HTTPException(status_code=423, detail=str(e))
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh(request: Request, body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await refresh_access_token(db, body.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user: User = Depends(get_current_user),
):
    """Revoke the current access token."""
    blacklist = getattr(request.app.state, "token_blacklist", None)
    if not blacklist:
        return {"message": "Logged out"}

    try:
        payload = decode_token(credentials.credentials)
        jti = payload.get("jti")
        exp = payload.get("exp", 0)
        if jti:
            import time
            ttl = max(int(exp - time.time()), 0)
            if ttl > 0:
                await blacklist.revoke(jti, ttl)
    except Exception:
        pass

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
