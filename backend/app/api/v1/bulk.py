from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.backend_server import BackendServer
from app.models.domain import Domain
from app.models.user import User
from app.security.rbac import require_permission

router = APIRouter(prefix="/bulk", tags=["bulk"])


class BulkDomainEntry(BaseModel):
    hostname: str = Field(min_length=1, max_length=253)
    backend_name: str = Field(min_length=1)
    force_https: bool = True
    enable_websocket: bool = False


class BulkDomainRequest(BaseModel):
    domains: list[BulkDomainEntry] = Field(min_length=1, max_length=50)


@router.post("/domains")
async def bulk_create_domains(
    data: BulkDomainRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("domain.create")),
):
    """Create multiple domains at once."""
    # Pre-fetch all backends
    backend_result = await db.execute(select(BackendServer))
    backends_by_name = {b.name: b for b in backend_result.scalars().all()}

    created = 0
    skipped = 0
    errors = []

    for entry in data.domains:
        # Check backend exists
        backend = backends_by_name.get(entry.backend_name)
        if not backend:
            errors.append(f"{entry.hostname}: backend '{entry.backend_name}' not found")
            continue

        # Check domain doesn't already exist
        existing = await db.execute(select(Domain).where(Domain.hostname == entry.hostname.lower()))
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        domain = Domain(
            hostname=entry.hostname.lower(),
            backend_id=backend.id,
            is_active=True,
            force_https=entry.force_https,
            enable_websocket=entry.enable_websocket,
        )
        db.add(domain)
        created += 1

    await db.commit()

    return {
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "total": len(data.domains),
    }
