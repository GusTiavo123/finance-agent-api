import time

from app.application.ports import RateLimiterPort
from app.domain.models import RateLimitDecision


class InMemoryRateLimiter(RateLimiterPort):
    def __init__(self, limit: int, window_seconds: int):
        self._limit = limit
        self._window = window_seconds
        self._counters: dict[tuple[str, int], int] = {}

    async def acquire(self, key: str) -> RateLimitDecision:
        now = int(time.time())
        window_start = now - (now % self._window)
        counter_key = (key, window_start)
        self._counters = {k: v for k, v in self._counters.items() if k[1] == window_start}
        count = self._counters.get(counter_key, 0) + 1
        self._counters[counter_key] = count
        return RateLimitDecision(
            allowed=count <= self._limit,
            limit=self._limit,
            remaining=max(0, self._limit - count),
            retry_after_seconds=max(1, window_start + self._window - now),
        )
