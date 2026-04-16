import asyncio
import logging
import socket
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


def _resolve_sync(hostname: str) -> dict:
    """Resolve hostname to IP addresses (runs in thread pool)."""
    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        ips = list({r[4][0] for r in results})
        return {"success": True, "ips": ips}
    except socket.gaierror as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def check_dns(hostname: str) -> dict:
    """Check DNS resolution for a hostname."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _resolve_sync, hostname)


async def verify_domain_dns(hostname: str, expected_ip: str) -> dict:
    """Verify that a domain resolves to the expected IP (the proxy VM)."""
    result = await check_dns(hostname)

    if not result["success"]:
        return {
            "hostname": hostname,
            "status": "error",
            "message": f"DNS resolution failed: {result['error']}",
            "resolved_ips": [],
            "expected_ip": expected_ip,
            "match": False,
        }

    ips = result["ips"]
    match = expected_ip in ips

    return {
        "hostname": hostname,
        "status": "ok" if match else "mismatch",
        "message": "DNS points to correct IP" if match else f"DNS points to {', '.join(ips)} instead of {expected_ip}",
        "resolved_ips": ips,
        "expected_ip": expected_ip,
        "match": match,
    }


async def bulk_verify_dns(hostnames: list[str], expected_ip: str) -> list[dict]:
    """Verify DNS for multiple hostnames in parallel."""
    tasks = [verify_domain_dns(h, expected_ip) for h in hostnames]
    return await asyncio.gather(*tasks)
