import time

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import redirect

from apps.users.models import User



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


def reset_quota_if_new_day(user):
    today = timezone.localdate()
    if user.last_quota_reset != today:
        User.objects.filter(pk=user.pk).update(
            used_today=0,
            last_quota_reset=today,
        )


class QuotaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.quota_exceeded = False
        session = getattr(request, "session", None)

        if _looks_like_search(request) and request.user.is_authenticated:
            reset_quota_if_new_day(request.user)
            request.user.refresh_from_db(fields=["used_today", "daily_quota", "last_quota_reset"])
            request.quota_exceeded = request.user.used_today >= request.user.daily_quota

        elif _looks_like_search(request) and not request.user.is_authenticated and session is not None:
            today = str(timezone.localdate())
            if session.get("anon_reset") != today:
                session["anon_used"] = 0
                session["anon_reset"] = today
            used = session.get("anon_used", 0)
            if used >= settings.ANON_DAILY_LIMIT:
                request.quota_exceeded = True

        response = self.get_response(request)

        cache_hit = getattr(request, "cache_hit", True)

        if _is_search_request(request) and request.user.is_authenticated:
            if not request.quota_exceeded and not cache_hit:
                User.objects.filter(pk=request.user.pk).update(
                    used_today=F("used_today") + 1
                )

        elif _is_search_request(request) and not request.user.is_authenticated and session is not None:
            if not request.quota_exceeded and not cache_hit:
                session["anon_used"] = session.get("anon_used", 0) + 1

        return response


class ThrottleMiddleware:
    """
    Limits search requests to SEARCH_THROTTLE_RATE per minute per user/IP.
    Uses a fixed window counter stored in Django cache (Redis in prod).
    Works correctly across multiple Gunicorn workers and container restarts.
    """

    WINDOW = 60  # seconds

    def __init__(self, get_response):
        self.get_response = get_response
        self.rate = getattr(settings, "SEARCH_THROTTLE_RATE", 8)

    def __call__(self, request):
        if _is_search_request(request):
            key = self._get_key(request)
            if self._is_throttled(key):
                return HttpResponse("Too many requests. Please wait a moment.", status=429)

        return self.get_response(request)

    def _get_key(self, request) -> str:
        window = int(time.time() // self.WINDOW)
        if request.user.is_authenticated:
            return f"throttle:user:{request.user.pk}:{window}"
        return f"throttle:ip:{self._get_ip(request)}:{window}"

    def _is_throttled(self, key: str) -> bool:
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=self.WINDOW * 2)
            count = 1
        return count > self.rate

    @staticmethod
    def _get_ip(request) -> str:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")


class LoginGateMiddleware:
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

        if (
            is_authenticated
            and not request.path.startswith("/users/accept-terms/")
            and not request.path.startswith("/users/delete/")
            and not request.path.startswith("/accounts/")
            and not getattr(request.user, "terms_accepted", True)
        ):
            return redirect("users:accept_terms")

        return response