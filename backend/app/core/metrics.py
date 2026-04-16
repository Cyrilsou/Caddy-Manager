import time

from prometheus_client import Counter, Gauge, Histogram, Info, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# App info
app_info = Info("caddy_panel", "Caddy Control Panel application info")
app_info.info({"version": "1.0.0"})

# HTTP metrics
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)
http_request_duration = Histogram(
    "http_request_duration_seconds", "HTTP request duration",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# Business metrics
backends_total = Gauge("caddy_backends_total", "Total backends configured")
backends_healthy = Gauge("caddy_backends_healthy", "Healthy backends")
backends_unhealthy = Gauge("caddy_backends_unhealthy", "Unhealthy backends")
domains_total = Gauge("caddy_domains_total", "Total domains configured")
domains_active = Gauge("caddy_domains_active", "Active domains")
certs_valid = Gauge("caddy_certs_valid", "Valid certificates")
certs_expiring = Gauge("caddy_certs_expiring_soon", "Certificates expiring soon")
certs_expired = Gauge("caddy_certs_expired", "Expired certificates")
config_version = Gauge("caddy_config_version", "Current active config version")
caddy_reachable = Gauge("caddy_reachable", "Caddy admin API reachable (1/0)")

# Auth metrics
login_attempts = Counter("caddy_login_attempts_total", "Login attempts", ["result"])
active_sessions = Gauge("caddy_active_sessions", "Approximate active sessions")


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = request.url.path
        # Normalize path to avoid cardinality explosion
        endpoint = _normalize_path(path)

        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start

        http_requests_total.labels(method, endpoint, response.status_code).inc()
        http_request_duration.labels(method, endpoint).observe(duration)

        return response


def _normalize_path(path: str) -> str:
    """Collapse IDs to {id} to limit label cardinality."""
    parts = path.split("/")
    normalized = []
    for part in parts:
        if part.isdigit():
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/".join(normalized)


async def update_business_metrics():
    """Called periodically by scheduler to update gauge values."""
    from sqlalchemy import select, func
    from app.database import async_session_factory
    from app.models.backend_server import BackendServer
    from app.models.domain import Domain
    from app.models.certificate import Certificate
    from app.models.config_version import ConfigVersion

    try:
        async with async_session_factory() as session:
            bt = (await session.execute(select(func.count()).select_from(BackendServer))).scalar() or 0
            bh = (await session.execute(
                select(func.count()).select_from(BackendServer).where(BackendServer.health_status == "healthy")
            )).scalar() or 0
            bu = (await session.execute(
                select(func.count()).select_from(BackendServer).where(BackendServer.health_status == "unhealthy")
            )).scalar() or 0

            dt = (await session.execute(select(func.count()).select_from(Domain))).scalar() or 0
            da = (await session.execute(
                select(func.count()).select_from(Domain).where(Domain.is_active == True)
            )).scalar() or 0

            cv = (await session.execute(
                select(func.count()).select_from(Certificate).where(Certificate.status == "valid")
            )).scalar() or 0
            ce = (await session.execute(
                select(func.count()).select_from(Certificate).where(Certificate.status == "expiring_soon")
            )).scalar() or 0
            cx = (await session.execute(
                select(func.count()).select_from(Certificate).where(Certificate.status == "expired")
            )).scalar() or 0

            active = await session.execute(
                select(ConfigVersion.version_number)
                .where(ConfigVersion.is_active == True)
                .limit(1)
            )
            ver = active.scalar_one_or_none() or 0

        backends_total.set(bt)
        backends_healthy.set(bh)
        backends_unhealthy.set(bu)
        domains_total.set(dt)
        domains_active.set(da)
        certs_valid.set(cv)
        certs_expiring.set(ce)
        certs_expired.set(cx)
        config_version.set(ver)
    except Exception:
        pass


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
