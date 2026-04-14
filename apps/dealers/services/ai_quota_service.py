from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

from apps.users.services.ai_quota_service import AiQuotaStatus


def get_anonymous_ai_quota_status_by_ip(client_ip: str):
    key = f"quota:anon_ai:{client_ip}:{timezone.localdate()}"
    used = cache.get(key, 0)
    limit = settings.ANON_AI_DAILY_LIMIT

    return AiQuotaStatus(
        allowed=used < limit,
        used=used,
        limit=limit,
    )


def consume_anonymous_ai_quota_by_ip(client_ip: str):
    key = f"quota:anon_ai:{client_ip}:{timezone.localdate()}"

    if not cache.get(key):
        cache.set(key, 0, timeout=86400)  # 1 day

    cache.incr(key)