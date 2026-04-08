from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db.models import F
from django.utils import timezone

from apps.users.models import User
from utils.http import _get_client_ip


@dataclass(frozen=True)
class AiQuotaStatus:
    allowed: bool
    used: int
    limit: int


def reset_ai_quota_if_new_day(user: User) -> None:
    """
    Reset per-user AI quota when local day changes.
    Uses Europe/Berlin local date via Django timezone settings.
    """
    today = timezone.localdate()

    if user.last_ai_quota_reset != today:
        User.objects.filter(pk=user.pk).update(
            ai_used_today=0,
            last_ai_quota_reset=today,
        )


def get_authenticated_ai_quota_status(user: User) -> AiQuotaStatus:
    """
    Return current AI quota status for authenticated user.
    Resets daily counters automatically on a new local day.
    """
    reset_ai_quota_if_new_day(user)
    user.refresh_from_db(fields=["ai_used_today", "ai_daily_quota", "last_ai_quota_reset"])

    return AiQuotaStatus(
        allowed=user.ai_used_today < user.ai_daily_quota,
        used=user.ai_used_today,
        limit=user.ai_daily_quota,
    )


def consume_authenticated_ai_quota(user: User) -> None:
    """
    Consume one AI quota unit for authenticated user.
    Uses atomic F() update to reduce race issues.
    """
    reset_ai_quota_if_new_day(user)
    User.objects.filter(pk=user.pk).update(ai_used_today=F("ai_used_today") + 1)


def _seconds_until_next_local_midnight() -> int:
    now = timezone.localtime()
    next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return int((next_midnight - now).total_seconds())


def _build_anon_ai_quota_key(request) -> str:
    """
    Build per-IP daily AI quota key for anonymous users.
    """
    today = timezone.localdate().isoformat()
    client_ip = _get_client_ip(request)
    return f"quota:anon_ai:{client_ip}:{today}"


def get_anonymous_ai_quota_status(request) -> AiQuotaStatus:
    """
    Return current AI quota status for anonymous user based on IP + local day.
    """
    key = _build_anon_ai_quota_key(request)
    used = cache.get(key, 0)
    limit = settings.ANON_AI_DAILY_LIMIT

    return AiQuotaStatus(
        allowed=used < limit,
        used=used,
        limit=limit,
    )


def consume_anonymous_ai_quota(request) -> None:
    """
    Consume one AI quota unit for anonymous user.
    Counter expires automatically at next local midnight.
    """
    key = _build_anon_ai_quota_key(request)
    timeout = _seconds_until_next_local_midnight()

    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=timeout)