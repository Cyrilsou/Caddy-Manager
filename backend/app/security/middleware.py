import ipaddress
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Cloudflare IPv4 ranges — only trust proxy headers from these IPs
# https://www.cloudflare.com/ips-v4/
CLOUDFLARE_IP_RANGES = [
    ipaddress.ip_network(cidr) for cidr in [
        "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22",
        "103.31.4.0/22", "141.101.64.0/18", "108.162.192.0/18",
        "190.93.240.0/20", "188.114.96.0/20", "197.234.240.0/22",
        "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
        "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
    ]
]

# Always trust these local IPs as reverse proxies (Caddy on same host)
TRUSTED_LOCAL = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
]


def _is_trusted_proxy(remote_ip: str) -> bool:
    """Check if the direct connection comes from a trusted proxy (Cloudflare or local)."""
    try:
        ip = ipaddress.ip_address(remote_ip)
    except ValueError:
        return False
    for net in TRUSTED_LOCAL:
        if ip in net:
            return True
    for net in CLOUDFLARE_IP_RANGES:
        if ip in net:
            return True
    return False


def get_client_ip(request: Request) -> str:
    """Extract real client IP. Only trust forwarded headers from verified proxies."""
    direct_ip = request.client.host if request.client else "127.0.0.1"

    if not _is_trusted_proxy(direct_ip):
        # Direct connection from untrusted source — ignore all forwarded headers
        return direct_ip

    # Request comes from a trusted proxy, safe to read forwarded headers
    return (
        request.headers.get("CF-Connecting-IP")
        or request.headers.get("X-Real-IP")
        or direct_ip
    )


class IPAllowlistMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allowed_ips: str = ""):
        super().__init__(app)
        self.allowed_networks = []
        if allowed_ips:
            for cidr in allowed_ips.split(","):
                cidr = cidr.strip()
                if cidr:
                    self.allowed_networks.append(ipaddress.ip_network(cidr, strict=False))

    async def dispatch(self, request: Request, call_next):
        if not self.allowed_networks:
            return await call_next(request)

        client_ip = get_client_ip(request)
        try:
            ip = ipaddress.ip_address(client_ip)
        except ValueError:
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})

        if not any(ip in net for net in self.allowed_networks):
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    MAX_BODY_SIZE = 1_048_576  # 1 MB

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            return JSONResponse(status_code=413, content={"detail": "Request body too large"})
        return await call_next(request)
