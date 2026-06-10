import time

from redis.asyncio import Redis

from app.application.ports import RateLimiterPort
from app.domain.models import RateLimitDecision


class RedisRateLimiter(RateLimiterPort):
    def __init__(self, redis: Redis, limit: int, window_seconds: int):
        self._redis = redis
        self._limit = limit
        self._window = window_seconds

    async def acquire(self, key: str) -> RateLimitDecision:
        now = int(time.time())
        window_start = now - (now % self._window)
        redis_key = f"ratelimit:{key}:{window_start}"
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(redis_key)
            pipe.expire(redis_key, self._window + 1)
            count, _ = await pipe.execute()
        retry_after = window_start + self._window - now
        return RateLimitDecision(
            allowed=count <= self._limit,
            limit=self._limit,
            remaining=max(0, self._limit - count),
            retry_after_seconds=max(1, retry_after),
        )
