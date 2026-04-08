from django.conf import settings
from common.services.rate_limiter import RedisRateLimiter, RateLimitExceeded


class AiRateLimitService:
    def __init__(self):
        self.limiter = RedisRateLimiter("ai")

    def check(self, user, request):
        identifier = self._get_identifier(user, request)

        self.limiter.check(
            identifier=identifier,
            limit=settings.AI_RATE_LIMIT_PER_MINUTE,
            window_sec=60,
        )

    def _get_identifier(self, user, request):
        if user.is_authenticated:
            return f"user:{user.id}"
        return f"anon:{self._get_ip(request)}"

    def _get_ip(self, request):
        return getattr(request, "client_ip", "unknown")