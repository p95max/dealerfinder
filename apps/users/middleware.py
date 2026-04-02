import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect

from utils.http import _get_client_ip


def _is_search_request(request) -> bool:
    match = getattr(request, "resolver_match", None)
    return (
        match is not None
        and match.url_name == "search"
        and match.app_name == "dealers"
        and request.method == "GET"
        and bool(request.GET.get("city"))
    )


class ThrottleMiddleware:
    """
    Limits search requests to SEARCH_THROTTLE_RATE per minute per user/IP.
    Uses Django cache (Redis in prod).
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
        return f"throttle:ip:{_get_client_ip(request)}:{window}"

    def _is_throttled(self, key: str) -> bool:
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=self.WINDOW * 2)
            count = 1
        return count > self.rate


class LoginGateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        is_authenticated = bool(user and user.is_authenticated)

        response = self.get_response(request)

        if (
            is_authenticated
            and not request.path.startswith("/users/accept-terms/")
            and not request.path.startswith("/users/delete/")
            and not request.path.startswith("/accounts/")
            and not getattr(request.user, "terms_accepted", True)
        ):
            return redirect("users:accept_terms")

        return response