import asyncio
import logging
import time
import os

logger = logging.getLogger(__name__)


async def run_speed_test() -> dict:
    """Measure server upload/download bandwidth using iperf-style byte counting."""
    results = {
        "download_mbps": 0.0,
        "upload_mbps": 0.0,
        "latency_ms": 0.0,
        "test_method": "http_transfer",
    }

    # Test 1: Download speed — fetch a known large file from Cloudflare's speed test endpoint
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            start = time.monotonic()
            r = await client.get("https://speed.cloudflare.com/__down?bytes=10000000")  # 10MB
            elapsed = time.monotonic() - start
            if r.status_code == 200:
                bytes_received = len(r.content)
                results["download_mbps"] = round((bytes_received * 8) / (elapsed * 1_000_000), 2)
    except Exception as e:
        logger.warning("Download speed test failed: %s", e)

    # Test 2: Upload speed — POST data to Cloudflare
    try:
        import httpx
        test_data = os.urandom(5_000_000)  # 5MB
        async with httpx.AsyncClient(timeout=30.0) as client:
            start = time.monotonic()
            r = await client.post(
                "https://speed.cloudflare.com/__up",
                content=test_data,
                headers={"Content-Type": "application/octet-stream"},
            )
            elapsed = time.monotonic() - start
            if r.status_code in (200, 204):
                results["upload_mbps"] = round((len(test_data) * 8) / (elapsed * 1_000_000), 2)
    except Exception as e:
        logger.warning("Upload speed test failed: %s", e)

    # Test 3: Latency — simple ping to Cloudflare
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            times = []
            for _ in range(3):
                start = time.monotonic()
                await client.get("https://1.1.1.1/cdn-cgi/trace")
                times.append((time.monotonic() - start) * 1000)
            results["latency_ms"] = round(sum(times) / len(times), 1)
    except Exception as e:
        logger.warning("Latency test failed: %s", e)

    return results


def recommend_cache_settings(speed_results: dict) -> dict:
    """Based on speed test results, recommend optimal Cloudflare cache settings."""
    upload_mbps = speed_results.get("upload_mbps", 0)
    download_mbps = speed_results.get("download_mbps", 0)

    recommendations = {
        "upload_mbps": upload_mbps,
        "download_mbps": download_mbps,
    }

    if upload_mbps < 50:
        # Slow server — aggressive caching to offload everything
        recommendations.update({
            "tier": "aggressive",
            "reason": f"Upload {upload_mbps} Mbps is low — aggressive CDN caching recommended",
            "cache_level": "aggressive",
            "browser_ttl": 14400,        # 4 hours
            "edge_ttl": 86400,           # 24 hours
            "always_online": True,
            "polish": "lossless",        # Image optimization
            "minify_js": True,
            "minify_css": True,
            "minify_html": True,
            "rocket_loader": True,
            "cache_everything": True,
        })
    elif upload_mbps < 200:
        # Medium server — balanced caching
        recommendations.update({
            "tier": "balanced",
            "reason": f"Upload {upload_mbps} Mbps is moderate — balanced caching recommended",
            "cache_level": "aggressive",
            "browser_ttl": 7200,         # 2 hours
            "edge_ttl": 43200,           # 12 hours
            "always_online": True,
            "polish": "lossless",
            "minify_js": True,
            "minify_css": True,
            "minify_html": False,
            "rocket_loader": False,
            "cache_everything": False,
        })
    else:
        # Fast server — light caching, let origin handle most
        recommendations.update({
            "tier": "light",
            "reason": f"Upload {upload_mbps} Mbps is fast — light caching sufficient",
            "cache_level": "basic",
            "browser_ttl": 1800,         # 30 min
            "edge_ttl": 7200,            # 2 hours
            "always_online": False,
            "polish": "off",
            "minify_js": False,
            "minify_css": False,
            "minify_html": False,
            "rocket_loader": False,
            "cache_everything": False,
        })

    return recommendations
