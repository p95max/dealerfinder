from django.conf import settings
from django.core.cache import cache


AI_SUMMARY_CACHE_KEY_PREFIX = "ai_summary"


def build_ai_summary_cache_key(place_id: str) -> str:
    """
    Build Redis cache key for dealer AI summary payload.
    """
    return f"{AI_SUMMARY_CACHE_KEY_PREFIX}:{place_id}"


def should_cache_ai_summary_payload(payload: dict | None) -> bool:
    """
    Cache only stable states.
    Do not cache pending or not_found responses.
    """
    if not payload or not isinstance(payload, dict):
        return False

    status = payload.get("status")
    return status in {"done", "failed"}


def get_cached_ai_summary_payload(place_id: str) -> dict | None:
    """
    Return cached AI summary payload from Redis or None on miss.
    """
    if not place_id:
        return None

    key = build_ai_summary_cache_key(place_id)
    payload = cache.get(key)

    if isinstance(payload, dict):
        return payload

    return None


def set_cached_ai_summary_payload(place_id: str, payload: dict) -> None:
    """
    Store AI summary payload in Redis if it is cacheable.
    """
    if not place_id or not should_cache_ai_summary_payload(payload):
        return

    key = build_ai_summary_cache_key(place_id)
    cache.set(
        key,
        payload,
        timeout=settings.AI_SUMMARY_CACHE_TTL_SECONDS,
    )


def delete_cached_ai_summary_payload(place_id: str) -> None:
    """
    Remove cached AI summary payload from Redis.
    """
    if not place_id:
        return

    key = build_ai_summary_cache_key(place_id)
    cache.delete(key)