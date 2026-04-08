from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


AI_SYSTEM_QUOTA_CACHE_KEY = "quota:ai_system"


@dataclass(frozen=True)
class AiSystemQuotaStatus:
    allowed: bool
    used: int
    limit: int


def _seconds_until_next_local_midnight() -> int:
    now = timezone.localtime()
    next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return int((next_midnight - now).total_seconds())


def get_ai_system_quota_status() -> AiSystemQuotaStatus:
    used = cache.get(AI_SYSTEM_QUOTA_CACHE_KEY, 0)
    limit = settings.MAX_AI_SUMMARIES_PER_DAY

    return AiSystemQuotaStatus(
        allowed=used < limit,
        used=used,
        limit=limit,
    )


def consume_ai_system_quota() -> None:
    timeout = _seconds_until_next_local_midnight()

    try:
        cache.incr(AI_SYSTEM_QUOTA_CACHE_KEY)
    except ValueError:
        cache.set(AI_SYSTEM_QUOTA_CACHE_KEY, 1, timeout=timeout)