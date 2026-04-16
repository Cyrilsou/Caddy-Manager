import time

import httpx
from fastapi import Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.backend_server import BackendServer
from app.models.domain import Domain
from app.models.user import User, utcnow
from app.schemas.backend import BackendCreate, BackendUpdate
from app.services.audit_service import log_audit


async def list_backends(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(
            BackendServer,
            func.count(Domain.id).label("domain_count"),
        )
        .outerjoin(Domain, Domain.backend_id == BackendServer.id)
        .group_by(BackendServer.id)
        .order_by(BackendServer.name)
    )

    items = []
    for b, domain_count in result.all():
        data = {
            "id": b.id, "name": b.name, "host": b.host, "port": b.port,
            "protocol": b.protocol, "health_check_enabled": b.health_check_enabled,
            "health_check_path": b.health_check_path,
            "health_check_interval_sec": b.health_check_interval_sec,
            "health_status": b.health_status, "health_checked_at": b.health_checked_at,
            "health_response_time_ms": b.health_response_time_ms,
            "tls_skip_verify": b.tls_skip_verify, "notes": b.notes,
            "domain_count": domain_count or 0,
            "created_at": b.created_at, "updated_at": b.updated_at,
        }
        items.append(data)
    return items


async def get_backend(db: AsyncSession, backend_id: int) -> BackendServer:
    result = await db.execute(select(BackendServer).where(BackendServer.id == backend_id))
    backend = result.scalar_one_or_none()
    if not backend:
        raise ValueError("Backend not found")
    return backend


async def create_backend(
    db: AsyncSession, data: BackendCreate, user: User, request: Request | None = None
) -> BackendServer:
    existing = await db.execute(
        select(BackendServer).where(BackendServer.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"Backend with name '{data.name}' already exists")

    backend = BackendServer(**data.model_dump())
    db.add(backend)
    await db.flush()

    await log_audit(db, user.id, "backend.create", "backend", backend.id,
                    {"name": data.name}, request)
    await db.commit()
    await db.refresh(backend)
    return backend


async def update_backend(
    db: AsyncSession, backend_id: int, data: BackendUpdate, user: User, request: Request | None = None
) -> BackendServer:
    backend = await get_backend(db, backend_id)
    update_data = data.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"] != backend.name:
        existing = await db.execute(
            select(BackendServer).where(BackendServer.name == update_data["name"])
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Backend with name '{update_data['name']}' already exists")

    ALLOWED_FIELDS = {
        "name", "host", "port", "protocol", "health_check_enabled",
        "health_check_path", "health_check_interval_sec", "tls_skip_verify", "notes",
    }
    for key, value in update_data.items():
        if key in ALLOWED_FIELDS:
            setattr(backend, key, value)

    await log_audit(db, user.id, "backend.update", "backend", backend.id,
                    update_data, request)
    await db.commit()
    await db.refresh(backend)
    return backend


async def delete_backend(
    db: AsyncSession, backend_id: int, user: User, request: Request | None = None
):
    backend = await get_backend(db, backend_id)

    domain_count = await db.execute(
        select(func.count()).select_from(Domain).where(Domain.backend_id == backend_id)
    )
    if (domain_count.scalar() or 0) > 0:
        raise ValueError("Cannot delete backend with associated domains")

    await log_audit(db, user.id, "backend.delete", "backend", backend.id,
                    {"name": backend.name}, request)
    await db.delete(backend)
    await db.commit()


BLOCKED_PORTS = {22, 25, 53, 6379, 5432, 3306, 27017, 11211, 2019}


async def check_backend_health(db: AsyncSession, backend_id: int) -> dict:
    backend = await get_backend(db, backend_id)

    # SSRF protection: block probing internal services
    if backend.port in BLOCKED_PORTS:
        return {"status": "error", "error": f"Port {backend.port} is blocked for security"}

    url = f"{backend.protocol}://{backend.host}:{backend.port}{backend.health_check_path}"

    try:
        async with httpx.AsyncClient(timeout=5.0, verify=not backend.tls_skip_verify) as client:
            start = time.monotonic()
            response = await client.get(url)
            elapsed_ms = int((time.monotonic() - start) * 1000)

        status = "healthy" if 200 <= response.status_code < 400 else "unhealthy"
        backend.health_status = status
        backend.health_response_time_ms = elapsed_ms
        backend.health_checked_at = utcnow()
        await db.commit()

        return {
            "status": status,
            "status_code": response.status_code,
            "response_time_ms": elapsed_ms,
        }
    except Exception as e:
        backend.health_status = "unhealthy"
        backend.health_response_time_ms = None
        backend.health_checked_at = utcnow()
        await db.commit()

        return {"status": "unhealthy", "error": str(e)}
