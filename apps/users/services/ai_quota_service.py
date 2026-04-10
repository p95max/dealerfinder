from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from utils.http import _get_client_ip


@dataclass(frozen=True)
class AiQuotaStatus:
    allowed: bool
    used: int
    limit: int


def _seconds_until_next_local_midnight() -> int:
    now = timezone.localtime()
    next_midnight = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    ) + timedelta(days=1)
    return int((next_midnight - now).total_seconds())


def _build_authenticated_ai_quota_key(user) -> str:
    today = timezone.localdate().isoformat()
    return f"quota:ai:user:{user.pk}:{today}"


def _build_anon_ai_quota_key(request) -> str:
    today = timezone.localdate().isoformat()
    client_ip = _get_client_ip(request)
    return f"quota:anon_ai:{client_ip}:{today}"


def _get_counter_value(key: str) -> int:
    value = cache.get(key, 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _increment_counter(key: str, *, timeout: int) -> int:
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=timeout)
        return 1


def get_authenticated_ai_quota_status(user) -> AiQuotaStatus:
    key = _build_authenticated_ai_quota_key(user)
    used = _get_counter_value(key)
    limit = int(getattr(user, "ai_daily_quota", settings.FREE_AI_DAILY_LIMIT))

    return AiQuotaStatus(
        allowed=used < limit,
        used=used,
        limit=limit,
    )


def consume_authenticated_ai_quota(user) -> int:
    key = _build_authenticated_ai_quota_key(user)
    timeout = _seconds_until_next_local_midnight()
    return _increment_counter(key, timeout=timeout)


def get_anonymous_ai_quota_status(request) -> AiQuotaStatus:
    key = _build_anon_ai_quota_key(request)
    used = _get_counter_value(key)
    limit = settings.ANON_AI_DAILY_LIMIT

    return AiQuotaStatus(
        allowed=used < limit,
        used=used,
        limit=limit,
    )


def consume_anonymous_ai_quota(request) -> int:
    key = _build_anon_ai_quota_key(request)
    timeout = _seconds_until_next_local_midnight()
    return _increment_counter(key, timeout=timeout)