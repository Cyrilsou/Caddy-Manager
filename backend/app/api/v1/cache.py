from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.security.rbac import require_permission
from app.services.cloudflare_cache_service import CloudflareCacheService
from app.services.local_cache_service import LocalCacheService
from app.services.speedtest_service import run_speed_test, recommend_cache_settings

router = APIRouter(prefix="/cache", tags=["cache"])


def _get_cache_service() -> CloudflareCacheService:
    if not settings.CLOUDFLARE_API_TOKEN:
        raise HTTPException(status_code=400, detail="Cloudflare API token not configured")
    return CloudflareCacheService(settings.CLOUDFLARE_API_TOKEN)


# === Speed Test ===

@router.post("/speedtest")
async def speed_test(_: User = Depends(require_permission("settings.read"))):
    """Run a server bandwidth speed test against Cloudflare."""
    results = await run_speed_test()
    recommendations = recommend_cache_settings(results)
    return {
        "speed_test": results,
        "recommendations": recommendations,
    }


# === Cache Purge ===

class PurgeUrlsRequest(BaseModel):
    zone_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    urls: list[str] = Field(min_length=1, max_length=30)


class PurgeHostsRequest(BaseModel):
    zone_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    hosts: list[str] = Field(min_length=1, max_length=30)


@router.post("/purge/all")
async def purge_all(
    zone_id: str = Query(pattern=r"^[a-f0-9]{32}$"),
    _: User = Depends(require_permission("cloudflare.write")),
):
    """Purge ALL cached content for a zone."""
    svc = _get_cache_service()
    try:
        result = await svc.purge_everything(zone_id)
        return {"message": "Cache purged successfully", "result": result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/purge/urls")
async def purge_urls(
    data: PurgeUrlsRequest,
    _: User = Depends(require_permission("cloudflare.write")),
):
    """Purge specific URLs from cache (max 30)."""
    svc = _get_cache_service()
    try:
        result = await svc.purge_urls(data.zone_id, data.urls)
        return {"message": f"Purged {len(data.urls)} URL(s)", "result": result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/purge/hosts")
async def purge_hosts(
    data: PurgeHostsRequest,
    _: User = Depends(require_permission("cloudflare.write")),
):
    """Purge all cache for specific hostnames."""
    svc = _get_cache_service()
    try:
        result = await svc.purge_by_hosts(data.zone_id, data.hosts)
        return {"message": f"Purged cache for {len(data.hosts)} host(s)", "result": result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# === Cache Settings ===

@router.get("/settings/{zone_id}")
async def get_cache_settings(
    zone_id: str,
    _: User = Depends(require_permission("cloudflare.read")),
):
    """Get all cache-related settings for a zone."""
    svc = _get_cache_service()
    try:
        return {
            "cache_level": await svc.get_cache_level(zone_id),
            "browser_cache_ttl": await svc.get_browser_cache_ttl(zone_id),
            "always_online": await svc.get_always_online(zone_id),
            "polish": await svc.get_polish(zone_id),
            "minify": await svc.get_minify(zone_id),
            "rocket_loader": await svc.get_rocket_loader(zone_id),
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


class CacheSettingsUpdate(BaseModel):
    cache_level: str | None = Field(default=None, pattern=r"^(aggressive|basic|simplified)$")
    browser_cache_ttl: int | None = Field(default=None, ge=0, le=31536000)
    always_online: bool | None = None
    polish: str | None = Field(default=None, pattern=r"^(off|lossless|lossy)$")
    minify_js: bool | None = None
    minify_css: bool | None = None
    minify_html: bool | None = None
    rocket_loader: bool | None = None


@router.patch("/settings/{zone_id}")
async def update_cache_settings(
    zone_id: str,
    data: CacheSettingsUpdate,
    _: User = Depends(require_permission("cloudflare.write")),
):
    """Update individual cache settings for a zone."""
    svc = _get_cache_service()
    applied = {}

    try:
        if data.cache_level is not None:
            await svc.set_cache_level(zone_id, data.cache_level)
            applied["cache_level"] = data.cache_level

        if data.browser_cache_ttl is not None:
            await svc.set_browser_cache_ttl(zone_id, data.browser_cache_ttl)
            applied["browser_cache_ttl"] = data.browser_cache_ttl

        if data.always_online is not None:
            await svc.set_always_online(zone_id, data.always_online)
            applied["always_online"] = data.always_online

        if data.polish is not None:
            await svc.set_polish(zone_id, data.polish)
            applied["polish"] = data.polish

        if any(x is not None for x in [data.minify_js, data.minify_css, data.minify_html]):
            current = await svc.get_minify(zone_id)
            js = data.minify_js if data.minify_js is not None else current.get("js") == "on"
            css = data.minify_css if data.minify_css is not None else current.get("css") == "on"
            html = data.minify_html if data.minify_html is not None else current.get("html") == "on"
            await svc.set_minify(zone_id, js, css, html)
            applied["minify"] = {"js": js, "css": css, "html": html}

        if data.rocket_loader is not None:
            await svc.set_rocket_loader(zone_id, data.rocket_loader)
            applied["rocket_loader"] = data.rocket_loader

        return {"message": "Settings updated", "applied": applied}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# === Auto-Optimize ===

@router.post("/auto-optimize/{zone_id}")
async def auto_optimize(
    zone_id: str,
    _: User = Depends(require_permission("settings.write")),
):
    """Run speed test, then auto-apply optimal cache settings to the zone."""
    svc = _get_cache_service()

    speed_results = await run_speed_test()
    recommendations = recommend_cache_settings(speed_results)
    applied = await svc.apply_recommendations(zone_id, recommendations)

    return {
        "speed_test": speed_results,
        "recommendations": recommendations,
        "applied": applied,
    }


# === Analytics ===

@router.get("/analytics/{zone_id}")
async def cache_analytics(
    zone_id: str,
    _: User = Depends(require_permission("cloudflare.read")),
):
    """Get cache hit ratio and bandwidth analytics for a zone."""
    svc = _get_cache_service()
    try:
        return await svc.get_cache_analytics(zone_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# =============================================================================
# LOCAL CDN CACHE (Souin — used when Cloudflare is not configured)
# =============================================================================

def _get_local_cache() -> LocalCacheService:
    return LocalCacheService()


@router.get("/local/stats")
async def local_cache_stats(_: User = Depends(require_permission("settings.read"))):
    """Get local Caddy cache statistics."""
    return await _get_local_cache().get_stats()


@router.post("/local/purge/all")
async def local_purge_all(_: User = Depends(require_permission("cloudflare.write"))):
    """Purge entire local Caddy cache."""
    success = await _get_local_cache().purge_all()
    if not success:
        raise HTTPException(status_code=502, detail="Failed to purge local cache (cache may not be active)")
    return {"message": "Local cache purged"}


class LocalPurgeDomainRequest(BaseModel):
    hostname: str = Field(min_length=1, max_length=253)


@router.post("/local/purge/domain")
async def local_purge_domain(
    data: LocalPurgeDomainRequest,
    _: User = Depends(require_permission("cloudflare.write")),
):
    """Purge local cache for a specific domain."""
    success = await _get_local_cache().purge_by_domain(data.hostname)
    if not success:
        raise HTTPException(status_code=502, detail=f"Failed to purge cache for {data.hostname}")
    return {"message": f"Cache purged for {data.hostname}"}


class LocalPurgeUrlRequest(BaseModel):
    url: str = Field(min_length=1)


@router.post("/local/purge/url")
async def local_purge_url(
    data: LocalPurgeUrlRequest,
    _: User = Depends(require_permission("cloudflare.write")),
):
    """Purge a specific URL from local cache."""
    success = await _get_local_cache().purge_by_url(data.url)
    if not success:
        raise HTTPException(status_code=502, detail=f"Failed to purge URL")
    return {"message": f"URL purged from cache"}


@router.get("/local/entries/{hostname}")
async def local_cache_entries(
    hostname: str,
    _: User = Depends(require_permission("settings.read")),
):
    """List cached entries for a specific domain."""
    entries = await _get_local_cache().get_entries_by_domain(hostname)
    return {"hostname": hostname, "entries": entries, "count": len(entries)}


@router.get("/status")
async def cache_status(_: User = Depends(require_permission("settings.read"))):
    """Check which cache system is active (Cloudflare CDN or Local CDN)."""
    has_cf = bool(settings.CLOUDFLARE_API_TOKEN)
    local_stats = await _get_local_cache().get_stats()
    local_active = "error" not in local_stats

    return {
        "cloudflare_cdn": has_cf,
        "local_cdn": local_active and not has_cf,
        "local_cdn_available": local_active,
        "active": "cloudflare" if has_cf else ("local" if local_active else "none"),
        "local_entries": local_stats.get("total_entries", 0),
    }
