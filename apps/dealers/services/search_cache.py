from datetime import timedelta

from django.utils import timezone
from django.conf import settings

from apps.dealers.models import SearchCache


TTL = timedelta(hours=settings.CACHE_TTL_HOURS)


def get_cache(query_key):
    try:
        cache = SearchCache.objects.get(query_key=query_key)

        if timezone.now() - cache.created_at < TTL:
            return cache.results_json

        return None
    except SearchCache.DoesNotExist:
        return None


def set_cache(query_key, data):
    SearchCache.objects.update_or_create(
        query_key=query_key,
        defaults={"results_json": data},
    )