import time
from django.conf import settings
from django.core.cache import cache

class RateLimitExceeded(Exception):
    pass


class RedisRateLimiter:
    """
    Sliding window rate limiter using Redis ZSET.
    """

    def __init__(self, key_prefix: str):
        self.key_prefix = key_prefix

    def _key(self, identifier: str) -> str:
        return f"rl:{self.key_prefix}:{identifier}"

    def check(self, identifier: str, limit: int, window_sec: int):
        """
        Raises RateLimitExceeded if limit exceeded.
        """
        key = self._key(identifier)
        now = time.time()
        window_start = now - window_sec

        pipe = cache.client.get_client(write=True).pipeline()

        pipe.zremrangebyscore(key, 0, window_start)

        pipe.zadd(key, {f"{now}:{id(self)}": now})

        pipe.zcard(key)

        pipe.expire(key, window_sec)

        _, _, count, _ = pipe.execute()

        if count > limit:
            raise RateLimitExceeded(f"Rate limit exceeded: {limit}/{window_sec}s")