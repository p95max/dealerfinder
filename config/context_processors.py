from django.conf import settings

from apps.users.services.quota_service import get_authenticated_quota_status
from apps.users.services.ai_quota_service import get_authenticated_ai_quota_status


def turnstile(request):
    return {
        "TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY,
    }

def user_quota_context(request):
    if not request.user.is_authenticated:
        return {}

    search_quota = get_authenticated_quota_status(request.user)
    ai_quota = get_authenticated_ai_quota_status(request.user)

    return {
        "search_quota_used": search_quota.used,
        "search_quota_limit": search_quota.limit,
        "ai_quota_used": ai_quota.used,
        "ai_quota_limit": ai_quota.limit,
    }