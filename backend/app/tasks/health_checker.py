import asyncio
import logging
import time

import httpx
from sqlalchemy import select

from app.database import async_session_factory
from app.models.backend_server import BackendServer
from app.models.user import utcnow

logger = logging.getLogger(__name__)

# Track previous status to only alert on transitions
_previous_status: dict[int, str] = {}


async def run_health_checks():
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(BackendServer).where(BackendServer.health_check_enabled == True)
            )
            backends = result.scalars().all()

            async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
                tasks = [_check_backend(client, backend) for backend in backends]
                await asyncio.gather(*tasks, return_exceptions=True)

            await session.commit()
    except Exception:
        logger.exception("Health check cycle failed")


async def _check_backend(client: httpx.AsyncClient, backend: BackendServer):
    old_status = _previous_status.get(backend.id, backend.health_status)
    url = f"{backend.protocol}://{backend.host}:{backend.port}{backend.health_check_path}"

    try:
        start = time.monotonic()
        response = await client.get(url)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        if 200 <= response.status_code < 400:
            backend.health_status = "healthy"
        else:
            backend.health_status = "unhealthy"
        backend.health_response_time_ms = elapsed_ms
    except Exception:
        backend.health_status = "unhealthy"
        backend.health_response_time_ms = None

    backend.health_checked_at = utcnow()
    _previous_status[backend.id] = backend.health_status

    # Alert + broadcast on status transitions
    if old_status != backend.health_status:
        try:
            from app.services.alert_service import alert_backend_down, alert_backend_recovered
            from app.api.v1.events import broadcast_event
            broadcast_event("backend_status", {
                "backend_id": backend.id, "name": backend.name,
                "status": backend.health_status, "old_status": old_status,
            })
            if backend.health_status == "unhealthy" and old_status in ("healthy", "unknown"):
                await alert_backend_down(backend.name, backend.host, backend.port)
            elif backend.health_status == "healthy" and old_status == "unhealthy":
                await alert_backend_recovered(backend.name, backend.host, backend.port)
        except Exception:
            logger.exception("Failed to send health alert for %s", backend.name)
