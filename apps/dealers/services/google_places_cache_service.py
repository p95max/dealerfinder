from django.conf import settings
from django.core.cache import cache


GOOGLE_PLACE_DETAILS_CACHE_KEY_PREFIX = "google_place_details"


def build_place_details_cache_key(place_id: str) -> str:
    """
    Build Redis cache key for Google Place Details payload.
    """
    return f"{GOOGLE_PLACE_DETAILS_CACHE_KEY_PREFIX}:{place_id}"


def get_cached_place_details(place_id: str) -> dict | None:
    """
    Return cached Google Place Details payload from Redis or None on miss.
    """
    if not place_id:
        return None

    key = build_place_details_cache_key(place_id)
    payload = cache.get(key)

    if isinstance(payload, dict):
        return payload

    return None


def set_cached_place_details(place_id: str, data: dict) -> None:
    """
    Store Google Place Details payload in Redis.
    """
    if not place_id or not isinstance(data, dict) or not data:
        return

    key = build_place_details_cache_key(place_id)
    cache.set(
        key,
        data,
        timeout=settings.PLACE_DETAILS_CACHE_TTL_SECONDS,
    )


def delete_cached_place_details(place_id: str) -> None:
    """
    Remove cached Google Place Details payload from Redis.
    """
    if not place_id:
        return

    key = build_place_details_cache_key(place_id)
    cache.delete(key)