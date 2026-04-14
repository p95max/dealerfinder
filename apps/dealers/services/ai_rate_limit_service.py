from django.conf import settings
from common.services.rate_limiter import RedisRateLimiter, RateLimitExceeded


class AiRateLimitService:
    def __init__(self):
        self.limiter = RedisRateLimiter("ai")

    def check(self, *, user=None, client_ip: str | None = None):
        identifier = self._get_identifier(user=user, client_ip=client_ip)

        self.limiter.check(
            identifier=identifier,
            limit=settings.AI_RATE_LIMIT_PER_MINUTE,
            window_sec=60,
        )

    def _get_identifier(self, *, user=None, client_ip: str | None = None):
        if user is not None and getattr(user, "is_authenticated", False):
            return f"user:{user.id}"

        return f"anon:{(client_ip or 'unknown').strip() or 'unknown'}"