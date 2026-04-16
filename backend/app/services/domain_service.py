from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.backend_server import BackendServer
from app.models.domain import Domain
from app.models.user import User
from app.schemas.domain import DomainCreate, DomainUpdate, DomainResponse
from app.services.audit_service import log_audit


async def list_domains(
    db: AsyncSession, search: str | None = None, is_active: bool | None = None,
    page: int = 1, per_page: int = 50,
) -> list[DomainResponse]:
    query = select(Domain).order_by(Domain.sort_order, Domain.hostname)

    if search:
        query = query.where(Domain.hostname.ilike(f"%{search}%"))
    if is_active is not None:
        query = query.where(Domain.is_active == is_active)

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    domains = result.scalars().all()

    items = []
    for d in domains:
        resp = DomainResponse(
            id=d.id, hostname=d.hostname, backend_id=d.backend_id,
            backend_name=d.backend.name if d.backend else "",
            backend_address=f"{d.backend.host}:{d.backend.port}" if d.backend else "",
            is_active=d.is_active, path_prefix=d.path_prefix,
            strip_prefix=d.strip_prefix, force_https=d.force_https,
            enable_websocket=d.enable_websocket, enable_cors=d.enable_cors,
            custom_headers=d.custom_headers, basic_auth=d.basic_auth,
            ip_allowlist=d.ip_allowlist, maintenance_mode=d.maintenance_mode,
            zone_id=d.zone_id, dns_record_id=d.dns_record_id,
            proxied=d.proxied, ssl_mode=d.ssl_mode,
            notes=d.notes, sort_order=d.sort_order,
            cert_status=d.certificate.status if d.certificate else None,
            created_at=d.created_at, updated_at=d.updated_at,
        )
        items.append(resp)
    return items


async def get_domain(db: AsyncSession, domain_id: int) -> Domain:
    result = await db.execute(select(Domain).where(Domain.id == domain_id))
    domain = result.scalar_one_or_none()
    if not domain:
        raise ValueError("Domain not found")
    return domain


async def create_domain(
    db: AsyncSession, data: DomainCreate, user: User, request: Request | None = None
) -> Domain:
    existing = await db.execute(
        select(Domain).where(Domain.hostname == data.hostname)
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"Domain '{data.hostname}' already exists")

    backend = await db.execute(
        select(BackendServer).where(BackendServer.id == data.backend_id)
    )
    if not backend.scalar_one_or_none():
        raise ValueError(f"Backend with id {data.backend_id} not found")

    domain = Domain(**data.model_dump())
    db.add(domain)
    await db.flush()

    await log_audit(db, user.id, "domain.create", "domain", domain.id,
                    {"hostname": data.hostname}, request)
    await db.commit()
    await db.refresh(domain)
    return domain


async def update_domain(
    db: AsyncSession, domain_id: int, data: DomainUpdate, user: User, request: Request | None = None
) -> Domain:
    domain = await get_domain(db, domain_id)
    update_data = data.model_dump(exclude_unset=True)

    if "hostname" in update_data and update_data["hostname"] != domain.hostname:
        existing = await db.execute(
            select(Domain).where(Domain.hostname == update_data["hostname"])
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Domain '{update_data['hostname']}' already exists")

    if "backend_id" in update_data:
        backend = await db.execute(
            select(BackendServer).where(BackendServer.id == update_data["backend_id"])
        )
        if not backend.scalar_one_or_none():
            raise ValueError(f"Backend with id {update_data['backend_id']} not found")

    for key, value in update_data.items():
        setattr(domain, key, value)

    await log_audit(db, user.id, "domain.update", "domain", domain.id,
                    update_data, request)
    await db.commit()
    await db.refresh(domain)
    return domain


async def delete_domain(
    db: AsyncSession, domain_id: int, user: User, request: Request | None = None
):
    domain = await get_domain(db, domain_id)

    await log_audit(db, user.id, "domain.delete", "domain", domain.id,
                    {"hostname": domain.hostname}, request)
    await db.delete(domain)
    await db.commit()


async def toggle_domain(
    db: AsyncSession, domain_id: int, user: User, request: Request | None = None
) -> Domain:
    domain = await get_domain(db, domain_id)
    domain.is_active = not domain.is_active

    await log_audit(db, user.id, "domain.toggle", "domain", domain.id,
                    {"hostname": domain.hostname, "is_active": domain.is_active}, request)
    await db.commit()
    await db.refresh(domain)
    return domain
