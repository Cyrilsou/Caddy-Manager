from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.domain import DomainCreate, DomainResponse, DomainUpdate
from app.security.rbac import require_permission
from app.services import domain_service

router = APIRouter(prefix="/domains", tags=["domains"])


@router.get("", response_model=list[DomainResponse])
async def list_domains(
    search: str | None = Query(None),
    is_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("domain.read")),
):
    return await domain_service.list_domains(db, search, is_active, page, per_page)


@router.get("/{domain_id}", response_model=DomainResponse)
async def get_domain(domain_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("domain.read"))):
    try:
        d = await domain_service.get_domain(db, domain_id)
        return DomainResponse(
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
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", response_model=DomainResponse, status_code=201)
async def create_domain(
    data: DomainCreate, request: Request,
    db: AsyncSession = Depends(get_db), user: User = Depends(require_permission("domain.create")),
):
    try:
        d = await domain_service.create_domain(db, data, user, request)
        return DomainResponse(
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
            cert_status=None, created_at=d.created_at, updated_at=d.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{domain_id}", response_model=DomainResponse)
async def update_domain(
    domain_id: int, data: DomainUpdate, request: Request,
    db: AsyncSession = Depends(get_db), user: User = Depends(require_permission("domain.update")),
):
    try:
        d = await domain_service.update_domain(db, domain_id, data, user, request)
        return DomainResponse(
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{domain_id}", status_code=204)
async def delete_domain(
    domain_id: int, request: Request,
    db: AsyncSession = Depends(get_db), user: User = Depends(require_permission("domain.delete")),
):
    try:
        await domain_service.delete_domain(db, domain_id, user, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{domain_id}/toggle")
async def toggle_domain(
    domain_id: int, request: Request,
    db: AsyncSession = Depends(get_db), user: User = Depends(require_permission("domain.update")),
):
    try:
        d = await domain_service.toggle_domain(db, domain_id, user, request)
        return {"id": d.id, "hostname": d.hostname, "is_active": d.is_active}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
