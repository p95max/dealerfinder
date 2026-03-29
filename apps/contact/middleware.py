from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.http import HttpResponse

from utils.http import _get_client_ip

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