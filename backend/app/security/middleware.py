import ipaddress

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


def get_client_ip(request: Request) -> str:
    return (
        request.headers.get("CF-Connecting-IP")
        or request.headers.get("X-Real-IP")
        or (request.client.host if request.client else "127.0.0.1")
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
