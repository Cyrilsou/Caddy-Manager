import redis.asyncio as redis

MAX_ATTEMPTS = 5
BAN_DURATION_SECONDS = 900
ATTEMPT_WINDOW_SECONDS = 300


class RedisFail2Ban:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def record_attempt(self, ip: str) -> None:
        key = f"fail2ban:attempts:{ip}"
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, ATTEMPT_WINDOW_SECONDS)
        await pipe.execute()

    async def is_banned(self, ip: str) -> bool:
        return await self.redis.exists(f"fail2ban:banned:{ip}") > 0

    async def check_and_ban(self, ip: str) -> bool:
        key = f"fail2ban:attempts:{ip}"
        attempts = await self.redis.get(key)
        if attempts and int(attempts) >= MAX_ATTEMPTS:
            await self.redis.setex(f"fail2ban:banned:{ip}", BAN_DURATION_SECONDS, "1")
            await self.redis.delete(key)
            return True
        return False

    async def clear(self, ip: str) -> None:
        await self.redis.delete(f"fail2ban:attempts:{ip}")
