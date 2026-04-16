from fastapi import Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.user import User

ROLE_HIERARCHY = {"admin": 3, "editor": 2, "viewer": 1}

PERMISSION_MAP = {
    "domain.read": "viewer",
    "domain.create": "editor",
    "domain.update": "editor",
    "domain.delete": "admin",
    "backend.read": "viewer",
    "backend.create": "editor",
    "backend.update": "editor",
    "backend.delete": "admin",
    "config.read": "viewer",
    "config.apply": "editor",
    "config.rollback": "admin",
    "cert.read": "viewer",
    "cert.refresh": "editor",
    "cloudflare.read": "viewer",
    "cloudflare.write": "editor",
    "audit.read": "viewer",
    "settings.read": "editor",
    "settings.write": "admin",
}


def has_permission(user: User, permission: str) -> bool:
    if user.is_superadmin:
        return True
    required_role = PERMISSION_MAP.get(permission, "admin")
    user_level = ROLE_HIERARCHY.get(user.role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 3)
    return user_level >= required_level


def require_permission(permission: str):
    async def checker(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: {permission} required",
            )
        return user
    return checker


require_admin = require_permission("settings.write")
require_editor = require_permission("domain.create")
require_viewer = require_permission("domain.read")
