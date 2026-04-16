import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.security.rbac import require_permission
from app.config import settings
from app.database import get_db
from app.models.backend_server import BackendServer
from app.models.certificate import Certificate
from app.models.config_version import ConfigVersion
from app.models.domain import Domain
from app.models.user import User
from app.schemas.dashboard import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats(db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("domain.read"))):
    # Single aggregated query for domains
    domain_stats = (await db.execute(
        select(
            func.count().label("total"),
            func.count().filter(Domain.is_active == True).label("active"),
        ).select_from(Domain)
    )).one()

    # Single aggregated query for backends
    backend_stats = (await db.execute(
        select(
            func.count().label("total"),
            func.count().filter(BackendServer.health_status == "healthy").label("healthy"),
            func.count().filter(BackendServer.health_status == "unhealthy").label("unhealthy"),
        ).select_from(BackendServer)
    )).one()

    # Single aggregated query for certificates
    cert_stats = (await db.execute(
        select(
            func.count().filter(Certificate.status == "valid").label("valid"),
            func.count().filter(Certificate.status == "expiring_soon").label("expiring"),
            func.count().filter(Certificate.status == "expired").label("expired"),
        ).select_from(Certificate)
    )).one()

    # Active config version
    active_config = await db.execute(
        select(ConfigVersion.version_number)
        .where(ConfigVersion.is_active == True)
        .order_by(ConfigVersion.version_number.desc())
        .limit(1)
    )
    config_version = active_config.scalar_one_or_none()

    # Caddy reachability check
    caddy_reachable = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.CADDY_ADMIN_URL}/config/")
            caddy_reachable = r.status_code in (200, 404)
    except Exception:
        pass

    unknown_backends = backend_stats.total - backend_stats.healthy - backend_stats.unhealthy

    return DashboardStats(
        total_domains=domain_stats.total,
        active_domains=domain_stats.active,
        total_backends=backend_stats.total,
        healthy_backends=backend_stats.healthy,
        unhealthy_backends=backend_stats.unhealthy,
        unknown_backends=unknown_backends,
        certs_valid=cert_stats.valid,
        certs_expiring_soon=cert_stats.expiring,
        certs_expired=cert_stats.expired,
        caddy_reachable=caddy_reachable,
        config_version=config_version,
    )
