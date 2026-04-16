import asyncio
import json
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.backend_server import BackendServer
from app.models.domain import Domain

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = [0.5, 1.5, 3.0]


class CaddyService:
    def __init__(self, admin_url: str | None = None):
        self.admin_url = admin_url or settings.CADDY_ADMIN_URL
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.admin_url,
                timeout=15.0,
            )
        return self._client

    async def _request_with_retry(
        self, method: str, path: str, max_retries: int = MAX_RETRIES, **kwargs
    ) -> httpx.Response:
        client = self._get_client()
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                r = await client.request(method, path, **kwargs)
                return r
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                last_exc = e
                if attempt < max_retries - 1:
                    delay = RETRY_BACKOFF_SECONDS[min(attempt, len(RETRY_BACKOFF_SECONDS) - 1)]
                    logger.warning("Caddy API %s %s attempt %d failed, retrying in %.1fs: %s",
                                   method, path, attempt + 1, delay, e)
                    await asyncio.sleep(delay)
            except Exception as e:
                raise e
        raise last_exc or httpx.ConnectError("Failed after retries")

    async def get_current_config(self) -> dict | None:
        try:
            r = await self._request_with_retry("GET", "/config/")
            if r.status_code == 200:
                return r.json()
            return None
        except Exception:
            return None

    async def load_config(self, config: dict) -> tuple[bool, str]:
        try:
            r = await self._request_with_retry(
                "POST", "/load",
                json=config,
                headers={"Content-Type": "application/json"},
            )
            if r.status_code == 200:
                return True, "Configuration applied successfully"
            else:
                return False, f"Caddy rejected config: {r.text}"
        except httpx.ConnectError:
            return False, "Cannot connect to Caddy admin API after retries"
        except Exception as e:
            return False, f"Error applying config: {str(e)}"

    async def is_reachable(self) -> bool:
        try:
            client = self._get_client()
            r = await client.get("/config/", timeout=3.0)
            return r.status_code in (200, 404)
        except Exception:
            return False

    async def build_config(self, db: AsyncSession) -> dict:
        result = await db.execute(
            select(Domain)
            .where(Domain.is_active == True)
            .order_by(Domain.sort_order, Domain.hostname)
        )
        domains = result.scalars().all()

        routes = []
        all_hostnames = []

        # Load additional upstreams for load balancing
        from app.models.domain_upstream import DomainUpstream
        upstream_result = await db.execute(select(DomainUpstream))
        all_upstreams = upstream_result.scalars().all()

        # Pre-resolve all backend IDs to host:port
        backend_result = await db.execute(select(BackendServer))
        all_backends = {b.id: b for b in backend_result.scalars().all()}

        extra_map: dict[int, list[BackendServer]] = {}
        for u in all_upstreams:
            b = all_backends.get(u.backend_id)
            if b:
                extra_map.setdefault(u.domain_id, []).append(b)

        for domain in domains:
            backend = domain.backend
            if not backend:
                continue

            extra_backends = extra_map.get(domain.id, [])
            all_hostnames.append(domain.hostname)
            route = self._build_route(domain, backend, extra_backends)
            routes.append(route)

        config = {
            "admin": {
                "listen": "localhost:2019",
            },
            "apps": {
                "http": {
                    "servers": {
                        "main": {
                            "listen": [":443", ":80"],
                            "routes": routes,
                            "automatic_https": {
                                "disable_redirects": False,
                            },
                        },
                    },
                },
            },
        }

        if all_hostnames and settings.CLOUDFLARE_API_TOKEN:
            config["apps"]["tls"] = {
                "automation": {
                    "policies": [
                        {
                            "subjects": all_hostnames,
                            "issuers": [
                                {
                                    "module": "acme",
                                    "challenges": {
                                        "dns": {
                                            "provider": {
                                                "name": "cloudflare",
                                                "api_token": "{env.CLOUDFLARE_API_TOKEN}",
                                            },
                                        },
                                    },
                                },
                            ],
                        },
                    ],
                },
            }

        return config

    def _build_route(self, domain: Domain, backend: BackendServer, extra_upstreams: list | None = None) -> dict:
        match_config: dict = {"host": [domain.hostname]}
        if domain.path_prefix and domain.path_prefix != "/":
            match_config["path"] = [f"{domain.path_prefix}*"]

        handlers = []

        # Redirect rule (takes priority over everything)
        if domain.redirect_url and domain.redirect_code in (301, 302):
            handlers.append({
                "handler": "static_response",
                "status_code": str(domain.redirect_code),
                "headers": {"Location": [domain.redirect_url]},
            })
            return {
                "@id": f"domain-{domain.id}",
                "match": [match_config],
                "handle": handlers,
                "terminal": True,
            }

        if domain.maintenance_mode:
            handlers.append({
                "handler": "static_response",
                "status_code": "503",
                "headers": {"Content-Type": ["text/html"]},
                "body": "<html><body><h1>Maintenance in progress</h1><p>This site is temporarily unavailable.</p></body></html>",
            })
            return {
                "@id": f"domain-{domain.id}",
                "match": [match_config],
                "handle": handlers,
                "terminal": True,
            }

        if domain.ip_allowlist:
            cidrs = [c.strip() for c in domain.ip_allowlist.split(",") if c.strip()]
            if cidrs:
                handlers.append({
                    "handler": "subroute",
                    "routes": [
                        {
                            "match": [{"not": [{"remote_ip": {"ranges": cidrs}}]}],
                            "handle": [{
                                "handler": "static_response",
                                "status_code": "403",
                                "body": "Forbidden",
                            }],
                            "terminal": True,
                        },
                    ],
                })

        # Basic authentication
        if domain.basic_auth:
            # Format: "user:hashed_password" (bcrypt hash)
            try:
                parts = domain.basic_auth.strip().split(":", 1)
                if len(parts) == 2:
                    handlers.append({
                        "handler": "authentication",
                        "providers": {
                            "http_basic": {
                                "accounts": [{
                                    "username": parts[0],
                                    "password": parts[1],
                                }],
                            },
                        },
                    })
            except Exception:
                pass

        if domain.strip_prefix and domain.path_prefix != "/":
            handlers.append({
                "handler": "rewrite",
                "strip_path_prefix": domain.path_prefix,
            })

        if domain.enable_cors:
            handlers.append({
                "handler": "headers",
                "response": {
                    "set": {
                        "Access-Control-Allow-Origin": ["*"],
                        "Access-Control-Allow-Methods": ["GET, POST, PUT, DELETE, OPTIONS"],
                        "Access-Control-Allow-Headers": ["Content-Type, Authorization"],
                    },
                },
            })

        transport: dict = {"protocol": "http"}
        if backend.protocol == "https":
            transport["tls"] = {}
            if backend.tls_skip_verify:
                transport["tls"]["insecure_skip_verify"] = True

        # Build upstream list (primary + additional for load balancing)
        upstreams = [{"dial": f"{backend.host}:{backend.port}"}]
        if extra_upstreams:
            for extra_b in extra_upstreams:
                upstreams.append({"dial": f"{extra_b.host}:{extra_b.port}"})

        upstream_config: dict = {
            "handler": "reverse_proxy",
            "upstreams": upstreams,
            "transport": transport,
        }

        if domain.lb_policy and len(upstreams) > 1:
            upstream_config["load_balancing"] = {"selection_policy": {"policy": domain.lb_policy}}

        upstream_config["headers"] = {
            "request": {
                "set": {
                    "X-Forwarded-Host": ["{http.request.host}"],
                    "X-Real-IP": ["{http.request.header.CF-Connecting-IP}"],
                    "X-Forwarded-Proto": ["{http.request.scheme}"],
                },
            },
        }

        if domain.custom_headers and isinstance(domain.custom_headers, dict):
            for key, value in domain.custom_headers.items():
                upstream_config["headers"]["request"]["set"][key] = [value]

        if backend.health_check_enabled:
            upstream_config["health_checks"] = {
                "active": {
                    "path": backend.health_check_path,
                    "interval": f"{backend.health_check_interval_sec}s",
                    "timeout": "5s",
                },
            }

        if domain.enable_websocket:
            upstream_config["transport"]["keepalive"] = {
                "max_idle_conns_per_host": 64,
            }
        else:
            upstream_config["transport"]["keepalive"] = {
                "max_idle_conns_per_host": 32,
            }

        handlers.append(upstream_config)

        # Compression
        encode_handler = {
            "handler": "encode",
            "encodings": {"zstd": {}, "gzip": {}},
        }

        return {
            "@id": f"domain-{domain.id}",
            "match": [match_config],
            "handle": [encode_handler] + handlers,
            "terminal": True,
        }


caddy_service = CaddyService()
