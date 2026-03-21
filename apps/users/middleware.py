import datetime

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