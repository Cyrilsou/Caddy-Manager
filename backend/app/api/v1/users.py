from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.security.auth import hash_password
from app.security.rbac import require_permission
from app.services.audit_service import log_audit

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    email: str | None = None
    role: str = Field(default="viewer", pattern=r"^(admin|editor|viewer)$")


class UserUpdate(BaseModel):
    email: str | None = None
    role: str | None = Field(default=None, pattern=r"^(admin|editor|viewer)$")
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None
    role: str
    is_active: bool
    is_superadmin: bool
    totp_enabled: bool
    last_login_at: str | None = None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("settings.write")),
):
    result = await db.execute(select(User).order_by(User.username))
    users = result.scalars().all()
    return [
        UserResponse(
            id=u.id, username=u.username, email=u.email, role=u.role,
            is_active=u.is_active, is_superadmin=u.is_superadmin,
            totp_enabled=u.totp_enabled,
            last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
        )
        for u in users
    ]


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate, request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("settings.write")),
):
    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"User '{data.username}' already exists")

    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        email=data.email,
        role=data.role,
        is_active=True,
        is_superadmin=False,
    )
    db.add(user)
    await db.flush()
    await log_audit(db, admin.id, "user.create", "user", user.id, {"username": data.username}, request)
    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id, username=user.username, email=user.email, role=user.role,
        is_active=user.is_active, is_superadmin=user.is_superadmin,
        totp_enabled=user.totp_enabled, last_login_at=None,
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int, data: UserUpdate, request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("settings.write")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_superadmin and data.is_active is False:
        raise HTTPException(status_code=400, detail="Cannot deactivate superadmin")

    if data.email is not None:
        user.email = data.email
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active

    await log_audit(db, admin.id, "user.update", "user", user.id, data.model_dump(exclude_unset=True), request)
    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id, username=user.username, email=user.email, role=user.role,
        is_active=user.is_active, is_superadmin=user.is_superadmin,
        totp_enabled=user.totp_enabled,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int, request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("settings.write")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_superadmin:
        raise HTTPException(status_code=400, detail="Cannot delete superadmin")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    await log_audit(db, admin.id, "user.delete", "user", user.id, {"username": user.username}, request)
    await db.delete(user)
    await db.commit()
