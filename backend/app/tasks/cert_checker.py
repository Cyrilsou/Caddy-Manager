import asyncio
import logging
import ssl
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from app.config import settings
from app.database import async_session_factory
from app.models.certificate import Certificate
from app.models.domain import Domain
from app.models.user import utcnow

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=20)


def _check_cert_sync(hostname: str) -> dict:
    """Run SSL cert check in a thread to avoid blocking the event loop."""
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                peer_cert = ssock.getpeercert()

        date_fmt = "%b %d %H:%M:%S %Y GMT"
        raw_before = peer_cert["notBefore"]
        raw_after = peer_cert["notAfter"]
        not_before = datetime.strptime(raw_before.replace("UTC", "GMT"), date_fmt).replace(tzinfo=timezone.utc)
        not_after = datetime.strptime(raw_after.replace("UTC", "GMT"), date_fmt).replace(tzinfo=timezone.utc)
        issuer_parts = dict(x[0] for x in peer_cert.get("issuer", []))
        issuer = issuer_parts.get("organizationName", "Unknown")
        serial = peer_cert.get("serialNumber", "")

        return {
            "success": True,
            "issuer": issuer,
            "not_before": not_before,
            "not_after": not_after,
            "serial_number": serial,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def run_cert_checks():
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Domain).where(Domain.is_active == True)
            )
            domains = result.scalars().all()

            loop = asyncio.get_event_loop()
            futures = [
                loop.run_in_executor(_executor, _check_cert_sync, domain.hostname)
                for domain in domains
            ]
            results = await asyncio.gather(*futures, return_exceptions=True)

            for domain, cert_data in zip(domains, results):
                if isinstance(cert_data, Exception):
                    logger.warning("Cert check failed for %s: %s", domain.hostname, cert_data)
                    await _update_cert(session, domain, {"success": False, "error": str(cert_data)})
                else:
                    await _update_cert(session, domain, cert_data)

            await session.commit()
    except Exception:
        logger.exception("Certificate check cycle failed")


async def _update_cert(session, domain: Domain, cert_data: dict):
    cert_result = await session.execute(
        select(Certificate).where(Certificate.domain_id == domain.id)
    )
    cert = cert_result.scalar_one_or_none()

    if not cert:
        cert = Certificate(domain_id=domain.id, hostname=domain.hostname)
        session.add(cert)

    if cert_data["success"]:
        cert.issuer = cert_data["issuer"]
        cert.not_before = cert_data["not_before"]
        cert.not_after = cert_data["not_after"]
        cert.serial_number = cert_data["serial_number"]
        cert.error_message = None

        now = datetime.now(timezone.utc)
        warning_threshold = now + timedelta(days=settings.CERT_EXPIRY_WARNING_DAYS)

        if cert_data["not_after"] < now:
            cert.status = "expired"
        elif cert_data["not_after"] < warning_threshold:
            cert.status = "expiring_soon"
        else:
            cert.status = "valid"
    else:
        cert.status = "error"
        cert.error_message = cert_data["error"]

    cert.last_checked_at = utcnow()
