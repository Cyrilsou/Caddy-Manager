from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.backends import router as backends_router
from app.api.v1.domains import router as domains_router
from app.api.v1.config import router as config_router
from app.api.v1.certificates import router as certificates_router
from app.api.v1.cloudflare import router as cloudflare_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.audit import router as audit_router
from app.api.v1.settings import router as settings_router
from app.api.v1.export_import import router as export_router
from app.api.v1.totp import router as totp_router
from app.api.v1.dns import router as dns_router
from app.api.v1.logs import router as logs_router
from app.api.v1.templates import router as templates_router
from app.api.v1.bulk import router as bulk_router
from app.api.v1.cache import router as cache_router
from app.api.v1.users import router as users_router
from app.api.v1.events import router as events_router
from app.api.v1.docker import router as docker_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(totp_router)
api_router.include_router(backends_router)
api_router.include_router(domains_router)
api_router.include_router(config_router)
api_router.include_router(certificates_router)
api_router.include_router(cloudflare_router)
api_router.include_router(dashboard_router)
api_router.include_router(audit_router)
api_router.include_router(settings_router)
api_router.include_router(export_router)
api_router.include_router(dns_router)
api_router.include_router(logs_router)
api_router.include_router(templates_router)
api_router.include_router(bulk_router)
api_router.include_router(cache_router)
api_router.include_router(users_router)
api_router.include_router(events_router)
api_router.include_router(docker_router)
