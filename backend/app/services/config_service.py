import hashlib
import json
import logging
from datetime import datetime, timezone

from fastapi import Request
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config_version import ConfigVersion
from app.models.user import User
from app.services.audit_service import log_audit
from app.services.caddy_service import caddy_service

logger = logging.getLogger(__name__)


def _hash_config(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


async def preview_config(db: AsyncSession) -> dict:
    config = await caddy_service.build_config(db)
    config_hash = _hash_config(config)

    active = await db.execute(
        select(ConfigVersion).where(ConfigVersion.is_active == True)
    )
    active_version = active.scalar_one_or_none()

    has_changes = True
    if active_version and active_version.config_hash == config_hash:
        has_changes = False

    return {
        "config_json": config,
        "has_changes": has_changes,
        "change_summary": "No changes" if not has_changes else "Configuration updated from current database state",
    }


async def apply_config(
    db: AsyncSession, user: User, request: Request | None = None
) -> dict:
    config = await caddy_service.build_config(db)
    config_hash = _hash_config(config)

    active_result = await db.execute(
        select(ConfigVersion).where(ConfigVersion.is_active == True)
    )
    active_version = active_result.scalar_one_or_none()

    if active_version and active_version.config_hash == config_hash:
        return {
            "success": True,
            "version_number": active_version.version_number,
            "message": "No changes to apply",
        }

    success, message = await caddy_service.load_config(config)

    if not success:
        await log_audit(db, user.id, "config.apply_failed", "config", None,
                        {"error": message}, request)
        await db.commit()
        raise ValueError(f"Failed to apply config: {message}")

    # Use SELECT ... FOR UPDATE to prevent race conditions on version numbering
    max_version = await db.execute(
        select(func.max(ConfigVersion.version_number)).with_for_update()
    )
    next_version = (max_version.scalar() or 0) + 1

    if active_version:
        active_version.is_active = False

    now = datetime.now(timezone.utc)
    new_version = ConfigVersion(
        version_number=next_version,
        config_json=json.dumps(config),
        config_hash=config_hash,
        is_active=True,
        applied_at=now,
        applied_by_id=user.id,
        change_summary="Configuration applied from panel",
    )
    db.add(new_version)

    await log_audit(db, user.id, "config.apply", "config", None,
                    {"version": next_version}, request)
    await db.commit()

    logger.info("Config version %d applied by user %s", next_version, user.username)

    return {
        "success": True,
        "version_number": next_version,
        "message": message,
    }


async def rollback_config(
    db: AsyncSession, version_id: int, user: User, request: Request | None = None
) -> dict:
    target_result = await db.execute(
        select(ConfigVersion).where(ConfigVersion.id == version_id)
    )
    target = target_result.scalar_one_or_none()
    if not target:
        raise ValueError("Config version not found")

    config = json.loads(target.config_json)
    success, message = await caddy_service.load_config(config)

    if not success:
        await log_audit(db, user.id, "config.rollback_failed", "config", version_id,
                        {"error": message}, request)
        await db.commit()
        raise ValueError(f"Failed to rollback: {message}")

    active_result = await db.execute(
        select(ConfigVersion).where(ConfigVersion.is_active == True)
    )
    active_version = active_result.scalar_one_or_none()
    if active_version:
        active_version.is_active = False

    max_version = await db.execute(
        select(func.max(ConfigVersion.version_number)).with_for_update()
    )
    next_version = (max_version.scalar() or 0) + 1

    now = datetime.now(timezone.utc)
    new_version = ConfigVersion(
        version_number=next_version,
        config_json=target.config_json,
        config_hash=target.config_hash,
        is_active=True,
        applied_at=now,
        applied_by_id=user.id,
        rollback_of_id=target.id,
        change_summary=f"Rollback to version {target.version_number}",
    )
    db.add(new_version)

    await log_audit(db, user.id, "config.rollback", "config", version_id,
                    {"from_version": target.version_number, "to_version": next_version}, request)
    await db.commit()

    logger.info("Rollback to version %d (new version %d) by user %s",
                target.version_number, next_version, user.username)

    return {
        "success": True,
        "version_number": next_version,
        "message": f"Rolled back to version {target.version_number}",
    }


async def list_versions(db: AsyncSession, page: int = 1, per_page: int = 20) -> list[ConfigVersion]:
    result = await db.execute(
        select(ConfigVersion)
        .order_by(desc(ConfigVersion.version_number))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return list(result.scalars().all())


async def get_version(db: AsyncSession, version_id: int) -> ConfigVersion:
    result = await db.execute(
        select(ConfigVersion).where(ConfigVersion.id == version_id)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise ValueError("Config version not found")
    return version


async def get_diff(db: AsyncSession, version_id: int) -> dict:
    target = await get_version(db, version_id)

    active_result = await db.execute(
        select(ConfigVersion).where(ConfigVersion.is_active == True)
    )
    active = active_result.scalar_one_or_none()

    old_json = json.dumps(json.loads(target.config_json), indent=2, sort_keys=True)
    new_json = json.dumps(
        json.loads(active.config_json) if active else {}, indent=2, sort_keys=True
    )

    import difflib
    diff = "\n".join(difflib.unified_diff(
        old_json.splitlines(),
        new_json.splitlines(),
        fromfile=f"v{target.version_number}",
        tofile=f"v{active.version_number}" if active else "current",
        lineterm="",
    ))

    return {
        "old_version": target.version_number,
        "new_version": active.version_number if active else 0,
        "diff": diff,
    }
