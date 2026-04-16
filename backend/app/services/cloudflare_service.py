import asyncio
import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"


class CloudflareAPIError(Exception):
    def __init__(self, errors: list):
        self.errors = errors
        message = "; ".join(e.get("message", "Unknown error") for e in errors)
        super().__init__(message)


class CloudflareRateLimiter:
    """Respect Cloudflare's 1200 requests per 5 minutes limit."""

    def __init__(self, max_requests: int = 1200, window_seconds: int = 300):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = datetime.now(timezone.utc).timestamp()
            self.timestamps = [t for t in self.timestamps if now - t < self.window_seconds]
            if len(self.timestamps) >= self.max_requests:
                sleep_time = self.window_seconds - (now - self.timestamps[0])
                logger.warning("Cloudflare rate limit reached, sleeping %.1fs", sleep_time)
                await asyncio.sleep(max(sleep_time, 1))
            self.timestamps.append(now)


class CloudflareService:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.rate_limiter = CloudflareRateLimiter()
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=CLOUDFLARE_API_BASE,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        await self.rate_limiter.acquire()
        client = self._get_client()
        response = await client.request(method, path, **kwargs)
        data = response.json()
        if not data.get("success"):
            logger.warning("Cloudflare API error on %s %s", method, path)
            raise CloudflareAPIError(data.get("errors", [{"message": "API request failed"}]))
        return data

    async def verify_token(self) -> bool:
        try:
            data = await self._request("GET", "/user/tokens/verify")
            return data["result"]["status"] == "active"
        except Exception:
            return False

    async def list_zones(self) -> list[dict]:
        data = await self._request("GET", "/zones", params={"per_page": 50})
        return data["result"]

    async def get_zone(self, zone_id: str) -> dict:
        data = await self._request("GET", f"/zones/{zone_id}")
        return data["result"]

    async def list_dns_records(self, zone_id: str, record_type: str | None = None) -> list[dict]:
        params: dict = {"per_page": 100}
        if record_type:
            params["type"] = record_type
        data = await self._request("GET", f"/zones/{zone_id}/dns_records", params=params)
        return data["result"]

    async def create_dns_record(
        self, zone_id: str, record_type: str, name: str, content: str,
        proxied: bool = True, ttl: int = 1,
    ) -> dict:
        payload = {
            "type": record_type,
            "name": name,
            "content": content,
            "proxied": proxied,
            "ttl": ttl,
        }
        data = await self._request("POST", f"/zones/{zone_id}/dns_records", json=payload)
        return data["result"]

    async def update_dns_record(
        self, zone_id: str, record_id: str, record_type: str, name: str,
        content: str, proxied: bool = True, ttl: int = 1,
    ) -> dict:
        payload = {
            "type": record_type,
            "name": name,
            "content": content,
            "proxied": proxied,
            "ttl": ttl,
        }
        data = await self._request("PUT", f"/zones/{zone_id}/dns_records/{record_id}", json=payload)
        return data["result"]

    async def delete_dns_record(self, zone_id: str, record_id: str) -> dict:
        return await self._request("DELETE", f"/zones/{zone_id}/dns_records/{record_id}")

    async def toggle_proxy(self, zone_id: str, record_id: str, proxied: bool) -> dict:
        data = await self._request("GET", f"/zones/{zone_id}/dns_records/{record_id}")
        r = data["result"]
        return await self.update_dns_record(
            zone_id, record_id, r["type"], r["name"], r["content"], proxied=proxied, ttl=r["ttl"],
        )

    async def get_ssl_mode(self, zone_id: str) -> str:
        data = await self._request("GET", f"/zones/{zone_id}/settings/ssl")
        return data["result"]["value"]

    async def set_ssl_mode(self, zone_id: str, mode: str) -> dict:
        return await self._request("PATCH", f"/zones/{zone_id}/settings/ssl", json={"value": mode})
