import time

from django.conf import settings
from django.utils import timezone
from django.db.models import F
from django.core.cache import cache
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect

from apps.users.models import User
from common.http import _get_client_ip


def _is_search_request(request) -> bool:
    match = request.resolver_match
    return (
        match is not None
        and match.url_name == "search"
        and match.app_name == "dealers"
        and request.method == "GET"
        and bool(request.GET.get("city"))
    )


def _looks_like_search(request) -> bool:
    return (
        request.method == "GET"
        and request.path == "/search/"
        and bool(request.GET.get("city"))
    )


class QuotaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.quota_exceeded = False

        if _looks_like_search(request) and request.user.is_authenticated:
            self._reset_if_new_day(request.user)
            request.user.refresh_from_db(fields=["used_today", "daily_quota", "last_quota_reset"])
            request.quota_exceeded = request.user.used_today >= request.user.daily_quota

        elif _looks_like_search(request) and not request.user.is_authenticated:
            today = str(timezone.localdate())
            if request.session.get("anon_reset") != today:
                request.session["anon_used"] = 0
                request.session["anon_reset"] = today
            used = request.session.get("anon_used", 0)
            if used >= settings.ANON_DAILY_LIMIT:
                request.quota_exceeded = True

        response = self.get_response(request)

        cache_hit = getattr(request, "cache_hit", True)

        if _is_search_request(request) and request.user.is_authenticated:
            if not request.quota_exceeded and not cache_hit:
                User.objects.filter(pk=request.user.pk).update(
                    used_today=F("used_today") + 1
                )

        elif _is_search_request(request) and not request.user.is_authenticated:
            if not request.quota_exceeded and not cache_hit:
                request.session["anon_used"] = request.session.get("anon_used", 0) + 1

        return response

    @staticmethod
    def _reset_if_new_day(user):
        today = timezone.localdate()
        if user.last_quota_reset != today:
            User.objects.filter(pk=user.pk).update(
                used_today=0,
                last_quota_reset=today,
            )


class ThrottleMiddleware:
    """
    Limits search requests to SEARCH_THROTTLE_RATE per minute per user/IP.
    Uses in-memory store — resets on worker restart, sufficient for single-process dev/prod.
    For multi-worker prod replace _store with Redis.
    """

    WINDOW = 60  # seconds
    _store: dict = {}

    def __init__(self, get_response):
        self.get_response = get_response
        self.rate = getattr(settings, "SEARCH_THROTTLE_RATE", 8)

    def __call__(self, request):
        if _is_search_request(request):
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


class ContactThrottleMiddleware(MiddlewareMixin):
    window_seconds = 600
    anon_limit = 3
    user_limit = 5

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.path != "/contact/" or request.method != "POST":
            return None

        if request.user.is_authenticated:
            ident = f"user:{request.user.pk}"
            limit = self.user_limit
        else:
            ident = f"ip:{_get_client_ip(request)}"
            limit = self.anon_limit

        key = f"contact_throttle:{ident}"
        current = cache.get(key, 0)

        if current >= limit:
            return HttpResponse(
                "Too many contact requests. Please try again later.",
                status=429,
            )

        cache.set(key, current + 1, timeout=self.window_seconds)
        return None


class LoginGateMiddleware:
    """Require Turnstile gate before starting Google OAuth flow."""

    GOOGLE_LOGIN_PATH_PREFIX = "/accounts/google/login/"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        is_authenticated = bool(user and user.is_authenticated)

        if (
            request.path.startswith(self.GOOGLE_LOGIN_PATH_PREFIX)
            and not is_authenticated
            and not request.session.get("turnstile_login_ok")
        ):
            return redirect("account_login")

        response = self.get_response(request)

        if is_authenticated:
            request.session.pop("turnstile_login_ok", None)

        return response