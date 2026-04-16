from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.models.user import User
from app.security.rbac import require_permission
from app.services.dns_checker import check_dns, verify_domain_dns, bulk_verify_dns

router = APIRouter(prefix="/dns", tags=["dns"])


class DNSCheckResponse(BaseModel):
    hostname: str
    status: str
    message: str
    resolved_ips: list[str]
    expected_ip: str
    match: bool


@router.get("/resolve")
async def resolve_hostname(
    hostname: str = Query(min_length=1),
    _: User = Depends(require_permission("domain.read")),
):
    """Resolve a hostname to its IP addresses."""
    return await check_dns(hostname)


@router.get("/verify", response_model=DNSCheckResponse)
async def verify_dns(
    hostname: str = Query(min_length=1),
    expected_ip: str = Query(min_length=1),
    _: User = Depends(require_permission("domain.read")),
):
    """Verify that a hostname resolves to the expected IP."""
    return await verify_domain_dns(hostname, expected_ip)


@router.post("/verify-all")
async def verify_all_domains(
    expected_ip: str = Query(min_length=1),
    _: User = Depends(require_permission("domain.read")),
):
    """Verify DNS for all active domains."""
    from sqlalchemy import select
    from app.database import async_session_factory
    from app.models.domain import Domain

    async with async_session_factory() as session:
        result = await session.execute(
            select(Domain.hostname).where(Domain.is_active == True)
        )
        hostnames = [r[0] for r in result.all()]

    return await bulk_verify_dns(hostnames, expected_ip)
