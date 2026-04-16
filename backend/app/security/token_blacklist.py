import redis.asyncio as redis

from app.config import settings

TOKEN_BLACKLIST_PREFIX = "token:blacklist:"


class TokenBlacklist:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        """Add a token's JTI to the blacklist until it would have expired."""
        key = f"{TOKEN_BLACKLIST_PREFIX}{jti}"
        await self.redis.setex(key, ttl_seconds, "1")

    async def is_revoked(self, jti: str) -> bool:
        """Check if a token's JTI has been revoked."""
        key = f"{TOKEN_BLACKLIST_PREFIX}{jti}"
        return await self.redis.exists(key) > 0

    async def revoke_all_for_user(self, user_id: int) -> None:
        """Revoke all tokens for a user by storing a global revocation timestamp."""
        key = f"token:revoke_all:{user_id}"
        import time
        await self.redis.setex(key, settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60, str(int(time.time())))

    async def is_user_revoked_before(self, user_id: int, issued_at: int) -> bool:
        """Check if all tokens for user were revoked after this token's iat."""
        key = f"token:revoke_all:{user_id}"
        revoked_at = await self.redis.get(key)
        if revoked_at and int(revoked_at) > issued_at:
            return True
        return False
