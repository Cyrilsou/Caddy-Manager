import logging

import httpx

logger = logging.getLogger(__name__)

CLOUDFLARE_API = "https://api.cloudflare.com/client/v4"


class CloudflareCacheService:
    def __init__(self, api_token: str):
        self._client: httpx.AsyncClient | None = None
        self.api_token = api_token

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=CLOUDFLARE_API,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def _req(self, method: str, path: str, **kwargs) -> dict:
        client = self._get_client()
        r = await client.request(method, path, **kwargs)
        data = r.json()
        if not data.get("success"):
            errors = data.get("errors", [{"message": "Unknown error"}])
            raise Exception("; ".join(e.get("message", "") for e in errors))
        return data

    # === Cache Purge ===

    async def purge_everything(self, zone_id: str) -> dict:
        """Purge ALL cached files for a zone."""
        data = await self._req("POST", f"/zones/{zone_id}/purge_cache", json={"purge_everything": True})
        return data["result"]

    async def purge_urls(self, zone_id: str, urls: list[str]) -> dict:
        """Purge specific URLs from cache (max 30 per call)."""
        data = await self._req("POST", f"/zones/{zone_id}/purge_cache", json={"files": urls[:30]})
        return data["result"]

    async def purge_by_prefix(self, zone_id: str, prefixes: list[str]) -> dict:
        """Purge by URL prefix (Enterprise only, graceful fallback)."""
        try:
            data = await self._req("POST", f"/zones/{zone_id}/purge_cache", json={"prefixes": prefixes})
            return data["result"]
        except Exception:
            logger.warning("Prefix purge not available (requires Enterprise), falling back to full purge")
            return await self.purge_everything(zone_id)

    async def purge_by_tags(self, zone_id: str, tags: list[str]) -> dict:
        """Purge by Cache-Tag header (Enterprise only, graceful fallback)."""
        try:
            data = await self._req("POST", f"/zones/{zone_id}/purge_cache", json={"tags": tags})
            return data["result"]
        except Exception:
            logger.warning("Tag purge not available (requires Enterprise)")
            return {}

    async def purge_by_hosts(self, zone_id: str, hosts: list[str]) -> dict:
        """Purge all cache for specific hostnames."""
        try:
            data = await self._req("POST", f"/zones/{zone_id}/purge_cache", json={"hosts": hosts})
            return data["result"]
        except Exception as e:
            logger.warning("Host purge failed: %s", e)
            return {}

    # === Cache Settings ===

    async def get_cache_level(self, zone_id: str) -> str:
        """Get cache level: aggressive, basic, simplified."""
        data = await self._req("GET", f"/zones/{zone_id}/settings/cache_level")
        return data["result"]["value"]

    async def set_cache_level(self, zone_id: str, level: str) -> dict:
        """Set cache level: aggressive, basic, simplified."""
        return await self._req("PATCH", f"/zones/{zone_id}/settings/cache_level", json={"value": level})

    async def get_browser_cache_ttl(self, zone_id: str) -> int:
        """Get browser cache TTL in seconds."""
        data = await self._req("GET", f"/zones/{zone_id}/settings/browser_cache_ttl")
        return data["result"]["value"]

    async def set_browser_cache_ttl(self, zone_id: str, ttl: int) -> dict:
        """Set browser cache TTL in seconds (0 = respect origin, or 30-31536000)."""
        return await self._req("PATCH", f"/zones/{zone_id}/settings/browser_cache_ttl", json={"value": ttl})

    async def get_always_online(self, zone_id: str) -> str:
        data = await self._req("GET", f"/zones/{zone_id}/settings/always_online")
        return data["result"]["value"]

    async def set_always_online(self, zone_id: str, enabled: bool) -> dict:
        return await self._req("PATCH", f"/zones/{zone_id}/settings/always_online",
                               json={"value": "on" if enabled else "off"})

    # === Performance / Optimization ===

    async def get_polish(self, zone_id: str) -> str:
        """Image optimization: off, lossless, lossy."""
        data = await self._req("GET", f"/zones/{zone_id}/settings/polish")
        return data["result"]["value"]

    async def set_polish(self, zone_id: str, mode: str) -> dict:
        return await self._req("PATCH", f"/zones/{zone_id}/settings/polish", json={"value": mode})

    async def get_minify(self, zone_id: str) -> dict:
        data = await self._req("GET", f"/zones/{zone_id}/settings/minify")
        return data["result"]["value"]

    async def set_minify(self, zone_id: str, js: bool, css: bool, html: bool) -> dict:
        return await self._req("PATCH", f"/zones/{zone_id}/settings/minify", json={
            "value": {
                "js": "on" if js else "off",
                "css": "on" if css else "off",
                "html": "on" if html else "off",
            }
        })

    async def get_rocket_loader(self, zone_id: str) -> str:
        data = await self._req("GET", f"/zones/{zone_id}/settings/rocket_loader")
        return data["result"]["value"]

    async def set_rocket_loader(self, zone_id: str, enabled: bool) -> dict:
        return await self._req("PATCH", f"/zones/{zone_id}/settings/rocket_loader",
                               json={"value": "on" if enabled else "off"})

    # === Analytics ===

    async def get_cache_analytics(self, zone_id: str) -> dict:
        """Get cache analytics summary (requests, bandwidth, cache hit ratio)."""
        data = await self._req("GET", f"/zones/{zone_id}/analytics/dashboard", params={"since": -1440})
        totals = data["result"]["totals"]
        requests = totals.get("requests", {})
        bandwidth = totals.get("bandwidth", {})

        cached_requests = requests.get("cached", 0)
        total_requests = requests.get("all", 1)
        cached_bandwidth = bandwidth.get("cached", 0)
        total_bandwidth = bandwidth.get("all", 1)

        return {
            "total_requests": total_requests,
            "cached_requests": cached_requests,
            "uncached_requests": requests.get("uncached", 0),
            "request_hit_ratio": round(cached_requests / max(total_requests, 1) * 100, 1),
            "total_bandwidth_mb": round(total_bandwidth / 1_048_576, 1),
            "cached_bandwidth_mb": round(cached_bandwidth / 1_048_576, 1),
            "bandwidth_hit_ratio": round(cached_bandwidth / max(total_bandwidth, 1) * 100, 1),
        }

    # === Apply Recommendations ===

    async def apply_recommendations(self, zone_id: str, recs: dict) -> dict:
        """Apply recommended cache settings to a zone."""
        applied = {}

        try:
            await self.set_cache_level(zone_id, recs.get("cache_level", "aggressive"))
            applied["cache_level"] = recs["cache_level"]
        except Exception as e:
            applied["cache_level_error"] = str(e)

        try:
            await self.set_browser_cache_ttl(zone_id, recs.get("browser_ttl", 7200))
            applied["browser_ttl"] = recs["browser_ttl"]
        except Exception as e:
            applied["browser_ttl_error"] = str(e)

        try:
            await self.set_always_online(zone_id, recs.get("always_online", False))
            applied["always_online"] = recs["always_online"]
        except Exception as e:
            applied["always_online_error"] = str(e)

        try:
            await self.set_polish(zone_id, recs.get("polish", "off"))
            applied["polish"] = recs["polish"]
        except Exception as e:
            applied["polish_error"] = str(e)

        try:
            await self.set_minify(
                zone_id,
                recs.get("minify_js", False),
                recs.get("minify_css", False),
                recs.get("minify_html", False),
            )
            applied["minify"] = {
                "js": recs.get("minify_js"),
                "css": recs.get("minify_css"),
                "html": recs.get("minify_html"),
            }
        except Exception as e:
            applied["minify_error"] = str(e)

        try:
            await self.set_rocket_loader(zone_id, recs.get("rocket_loader", False))
            applied["rocket_loader"] = recs["rocket_loader"]
        except Exception as e:
            applied["rocket_loader_error"] = str(e)

        applied["tier"] = recs.get("tier", "unknown")
        applied["reason"] = recs.get("reason", "")
        return applied
