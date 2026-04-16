import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select

from app.config import settings
from app.core.logging import RequestIDMiddleware, setup_logging
from app.database import async_session_factory, engine
from app.models.user import User
from app.security.auth import hash_password
from app.security.fail2ban import RedisFail2Ban
from app.security.token_blacklist import TokenBlacklist
from app.security.middleware import (
    IPAllowlistMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)

setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

redis_client: aioredis.Redis | None = None
fail2ban: RedisFail2Ban | None = None
token_blacklist: TokenBlacklist | None = None


async def create_initial_admin():
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.username == settings.ADMIN_USERNAME)
        )
        if result.scalar_one_or_none():
            return
        user = User(
            username=settings.ADMIN_USERNAME,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            is_active=True,
            is_superadmin=True,
        )
        session.add(user)
        await session.commit()
        logger.info("Initial admin user '%s' created", settings.ADMIN_USERNAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, fail2ban, token_blacklist

    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    fail2ban = RedisFail2Ban(redis_client)
    token_blacklist = TokenBlacklist(redis_client)
    app.state.redis = redis_client
    app.state.fail2ban = fail2ban
    app.state.token_blacklist = token_blacklist

    # Persistent HTTP client for internal services (Caddy, health checks)
    import httpx
    http_client = httpx.AsyncClient(timeout=15.0)
    app.state.http_client = http_client

    await create_initial_admin()

    from app.tasks.scheduler import start_scheduler
    scheduler = start_scheduler()

    logger.info("Caddy Control Panel started")
    yield

    scheduler.shutdown(wait=False)
    await http_client.aclose()
    await redis_client.close()
    await engine.dispose()
    logger.info("Caddy Control Panel stopped")


app = FastAPI(
    title="Caddy Control Panel",
    version="1.0.0",
    docs_url="/api/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan,
)

_is_local = settings.PANEL_DOMAIN in ("localhost", "127.0.0.1", "")

_allowed_hosts = [settings.PANEL_DOMAIN] if settings.PANEL_DOMAIN else []
_allowed_hosts.extend(["localhost", "127.0.0.1"])
if _is_local:
    _allowed_hosts.append("*")

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=_allowed_hosts,
)

_cors_origins = [
    f"https://{settings.PANEL_DOMAIN}",
    f"http://{settings.PANEL_DOMAIN}",
]
if _is_local or settings.ENVIRONMENT == "development":
    _cors_origins.extend([
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
    ])
if _is_local:
    # Allow access from any IP on the local network (no domain)
    _cors_origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=True,
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(IPAllowlistMiddleware, allowed_ips=settings.ALLOWED_IPS)
app.add_middleware(RequestSizeLimitMiddleware)

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


from app.api.v1.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/health/ready")
async def health_ready():
    checks = {"database": False, "redis": False}
    try:
        async with async_session_factory() as session:
            await session.execute(select(1))
            checks["database"] = True
    except Exception:
        pass
    try:
        if redis_client:
            await redis_client.ping()
            checks["redis"] = True
    except Exception:
        pass

    all_ok = all(checks.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={"status": "ready" if all_ok else "degraded", "checks": checks},
    )
