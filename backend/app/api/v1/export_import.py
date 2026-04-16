import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security.rbac import require_permission
from app.models.backend_server import BackendServer
from app.models.domain import Domain
from app.models.setting import Setting
from app.models.user import User

router = APIRouter(prefix="/export", tags=["export"])


@router.get("")
async def export_config(db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("settings.read"))):
    """Export all backends, domains, and settings as JSON for disaster recovery."""
    backends_result = await db.execute(select(BackendServer).order_by(BackendServer.name))
    domains_result = await db.execute(select(Domain).order_by(Domain.hostname))
    settings_result = await db.execute(select(Setting).where(Setting.is_secret == False))

    export_data = {
        "version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "backends": [
            {
                "name": b.name, "host": b.host, "port": b.port,
                "protocol": b.protocol, "health_check_enabled": b.health_check_enabled,
                "health_check_path": b.health_check_path,
                "health_check_interval_sec": b.health_check_interval_sec,
                "tls_skip_verify": b.tls_skip_verify, "notes": b.notes,
            }
            for b in backends_result.scalars().all()
        ],
        "domains": [
            {
                "hostname": d.hostname, "backend_name": d.backend.name if d.backend else "",
                "is_active": d.is_active, "path_prefix": d.path_prefix,
                "strip_prefix": d.strip_prefix, "force_https": d.force_https,
                "enable_websocket": d.enable_websocket, "enable_cors": d.enable_cors,
                "custom_headers": d.custom_headers, "maintenance_mode": d.maintenance_mode,
                "notes": d.notes, "sort_order": d.sort_order,
            }
            for d in domains_result.scalars().all()
        ],
        "settings": [
            {"key": s.key, "value": s.value}
            for s in settings_result.scalars().all()
        ],
    }

    return export_data


@router.post("/import")
async def import_config(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("settings.write")),
):
    """Import backends and domains from an exported JSON file."""
    if not user.is_superadmin:
        raise HTTPException(status_code=403, detail="Only superadmins can import configurations")

    content = await file.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    if "backends" not in data or "domains" not in data:
        raise HTTPException(status_code=400, detail="Missing backends or domains in export file")

    imported_backends = 0
    imported_domains = 0
    backend_map: dict[str, int] = {}

    for b_data in data["backends"]:
        existing = await db.execute(
            select(BackendServer).where(BackendServer.name == b_data["name"])
        )
        if existing.scalar_one_or_none():
            result = await db.execute(select(BackendServer).where(BackendServer.name == b_data["name"]))
            backend_map[b_data["name"]] = result.scalar_one().id
            continue
        backend = BackendServer(
            name=b_data["name"], host=b_data["host"], port=b_data["port"],
            protocol=b_data.get("protocol", "http"),
            health_check_enabled=b_data.get("health_check_enabled", False),
            health_check_path=b_data.get("health_check_path", "/"),
            health_check_interval_sec=b_data.get("health_check_interval_sec", 30),
            tls_skip_verify=b_data.get("tls_skip_verify", False),
            notes=b_data.get("notes"),
        )
        db.add(backend)
        await db.flush()
        backend_map[b_data["name"]] = backend.id
        imported_backends += 1

    for d_data in data["domains"]:
        existing = await db.execute(
            select(Domain).where(Domain.hostname == d_data["hostname"])
        )
        if existing.scalar_one_or_none():
            continue
        backend_name = d_data.get("backend_name", "")
        backend_id = backend_map.get(backend_name)
        if not backend_id:
            continue
        domain = Domain(
            hostname=d_data["hostname"], backend_id=backend_id,
            is_active=d_data.get("is_active", True),
            path_prefix=d_data.get("path_prefix", "/"),
            strip_prefix=d_data.get("strip_prefix", False),
            force_https=d_data.get("force_https", True),
            enable_websocket=d_data.get("enable_websocket", False),
            enable_cors=d_data.get("enable_cors", False),
            custom_headers=d_data.get("custom_headers"),
            maintenance_mode=d_data.get("maintenance_mode", False),
            notes=d_data.get("notes"),
            sort_order=d_data.get("sort_order", 0),
        )
        db.add(domain)
        imported_domains += 1

    await db.commit()

    return {
        "message": "Import completed",
        "backends_imported": imported_backends,
        "domains_imported": imported_domains,
    }
