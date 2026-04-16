import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LocalCacheService:
    """Manages the Souin cache-handler running inside Caddy."""

    def __init__(self, caddy_admin_url: str | None = None):
        self.base_url = f"{caddy_admin_url or settings.CADDY_ADMIN_URL}/souin-api/souin"
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def get_stats(self) -> dict:
        client = self._get_client()
        try:
            r = await client.get(self.base_url)
            if r.status_code == 200:
                data = r.json()
                keys = data if isinstance(data, list) else []
                # Group by domain
                domains: dict[str, int] = {}
                for key in keys:
                    key_str = str(key)
                    parts = key_str.split("/")
                    host = parts[2] if len(parts) > 2 and "." in parts[2] else "unknown"
                    domains[host] = domains.get(host, 0) + 1
                return {
                    "total_entries": len(keys),
                    "domains": domains,
                    "sample_keys": keys[:50],
                }
            return {"total_entries": 0, "domains": {}, "sample_keys": []}
        except Exception as e:
            logger.debug("Cache stats unavailable: %s", e)
            return {"total_entries": 0, "domains": {}, "sample_keys": [], "error": str(e)}

    async def purge_all(self) -> bool:
        client = self._get_client()
        try:
            r = await client.request("PURGE", self.base_url)
            return r.status_code in (200, 204, 204)
        except Exception as e:
            logger.warning("Purge all failed: %s", e)
            return False

    async def purge_by_domain(self, hostname: str) -> bool:
        client = self._get_client()
        try:
            r = await client.request("PURGE", f"{self.base_url}/{hostname}")
            return r.status_code in (200, 204)
        except Exception as e:
            logger.warning("Purge domain %s failed: %s", hostname, e)
            return False

    async def purge_by_url(self, url: str) -> bool:
        client = self._get_client()
        try:
            r = await client.request("PURGE", f"{self.base_url}/{url}")
            return r.status_code in (200, 204)
        except Exception as e:
            logger.warning("Purge URL failed: %s", e)
            return False

    async def get_entries_by_domain(self, hostname: str) -> list[str]:
        stats = await self.get_stats()
        keys = stats.get("sample_keys", [])
        return [k for k in keys if hostname in str(k)]
