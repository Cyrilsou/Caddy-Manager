import json
import logging

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def get(self, key: str) -> dict | None:
        try:
            data = await self.redis.get(f"cache:{key}")
            if data:
                return json.loads(data)
        except Exception:
            logger.debug("Cache miss for %s", key)
        return None

    async def set(self, key: str, value: dict, ttl_seconds: int = 15) -> None:
        try:
            await self.redis.setex(f"cache:{key}", ttl_seconds, json.dumps(value, default=str))
        except Exception:
            logger.debug("Cache set failed for %s", key)

    async def invalidate(self, key: str) -> None:
        try:
            await self.redis.delete(f"cache:{key}")
        except Exception:
            pass
