import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Domain
from app.services.cloudflare_service import CloudflareService

logger = logging.getLogger(__name__)


async def auto_create_dns(
    cf: CloudflareService,
    domain: Domain,
    proxy_ip: str,
    zone_id: str,
    proxied: bool = True,
) -> dict | None:
    """Create a DNS A record for a domain pointing to the proxy VM IP."""
    if not zone_id:
        return None

    try:
        record = await cf.create_dns_record(
            zone_id=zone_id,
            record_type="A",
            name=domain.hostname,
            content=proxy_ip,
            proxied=proxied,
        )
        logger.info("Created DNS record for %s -> %s", domain.hostname, proxy_ip)
        return record
    except Exception:
        logger.exception("Failed to create DNS record for %s", domain.hostname)
        return None


async def auto_delete_dns(
    cf: CloudflareService,
    zone_id: str,
    record_id: str,
) -> bool:
    """Delete a DNS record when removing a domain."""
    if not zone_id or not record_id:
        return False

    try:
        await cf.delete_dns_record(zone_id, record_id)
        logger.info("Deleted DNS record %s from zone %s", record_id, zone_id)
        return True
    except Exception:
        logger.exception("Failed to delete DNS record %s", record_id)
        return False
