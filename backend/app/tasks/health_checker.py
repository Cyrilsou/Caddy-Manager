import asyncio
import logging
import time

import httpx
from sqlalchemy import select

from app.database import async_session_factory
from app.models.backend_server import BackendServer
from app.models.user import utcnow

logger = logging.getLogger(__name__)


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
