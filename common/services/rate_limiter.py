import time
import uuid

from django_redis import get_redis_connection


class RateLimitExceeded(Exception):
    pass


class RedisRateLimiter:
    """
    Sliding window rate limiter using Redis ZSET (clean Redis client).
    """

    def __init__(self, key_prefix: str):
        self.key_prefix = key_prefix
        self.redis = get_redis_connection("default")

    def _key(self, identifier: str) -> str:
        return f"rl:{self.key_prefix}:{identifier}"

    def check(self, identifier: str, limit: int, window_sec: int):
        """
        Raises RateLimitExceeded if limit exceeded.
        """
        key = self._key(identifier)

        now = time.time()
        window_start = now - window_sec

        pipe = self.redis.pipeline()

        pipe.zremrangebyscore(key, 0, window_start)

        member = f"{now}:{uuid.uuid4()}"
        pipe.zadd(key, {member: now})

        pipe.zcard(key)

        pipe.expire(key, window_sec)

        _, _, count, _ = pipe.execute()

        if count > limit:
            raise RateLimitExceeded(
                f"Rate limit exceeded: {limit} requests / {window_sec}s"
            )