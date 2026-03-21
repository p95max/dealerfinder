import time

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone


class QuotaMiddleware:
    """Resets daily quota and increments used_today on search requests."""

    SEARCH_PATH = "/search/"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == self.SEARCH_PATH and request.method == "GET" and request.GET.get("city"):
            user = request.user
            if user.is_authenticated:
                self._reset_if_new_day(user)
                request.quota_exceeded = user.used_today >= user.daily_quota
            else:
                request.quota_exceeded = False
        else:
            request.quota_exceeded = False

        response = self.get_response(request)

        if request.path == self.SEARCH_PATH and request.method == "GET" and request.GET.get("city"):
            user = request.user
            if user.is_authenticated and not request.quota_exceeded:
                user.used_today += 1
                user.save(update_fields=["used_today"])

        return response

    @staticmethod
    def _reset_if_new_day(user):
        today = timezone.now().date()
        if user.last_quota_reset != today:
            user.used_today = 0
            user.last_quota_reset = today
            user.save(update_fields=["used_today", "last_quota_reset"])


class ThrottleMiddleware:
    """
    Limits search requests to SEARCH_THROTTLE_RATE per minute per user/IP.
    Uses in-memory store — resets on worker restart, sufficient for single-process dev/prod.
    For multi-worker prod replace _store with Redis.
    """

    SEARCH_PATH = "/search/"
    WINDOW = 60  # seconds

    _store: dict = {}

    def __init__(self, get_response):
        self.get_response = get_response
        self.rate = getattr(settings, "SEARCH_THROTTLE_RATE", 8)

    def __call__(self, request):
        if request.path == self.SEARCH_PATH and request.method == "GET" and request.GET.get("city"):
            key = self._get_key(request)
            if self._is_throttled(key):
                return HttpResponse("Too many requests. Please wait a moment.", status=429)

        return self.get_response(request)

    def _get_key(self, request):
        if request.user.is_authenticated:
            return f"throttle:user:{request.user.pk}"
        return f"throttle:ip:{self._get_ip(request)}"

    def _is_throttled(self, key: str) -> bool:
        now = time.time()
        window_start = now - self.WINDOW

        timestamps = self._store.get(key, [])
        timestamps = [t for t in timestamps if t > window_start]

        if len(timestamps) >= self.rate:
            self._store[key] = timestamps
            return True

        timestamps.append(now)
        self._store[key] = timestamps
        return False

    @staticmethod
    def _get_ip(request) -> str:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")