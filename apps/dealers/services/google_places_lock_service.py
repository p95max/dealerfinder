import time
import uuid
from dataclasses import dataclass

from django_redis import get_redis_connection


GOOGLE_PLACE_DETAILS_LOCK_KEY_PREFIX = "lock:google_place_details"
DEFAULT_GOOGLE_PLACE_DETAILS_LOCK_TTL_SECONDS = 20


@dataclass(frozen=True)
class GooglePlaceDetailsLock:
    key: str
    token: str


def _build_place_details_lock_key(place_id: str) -> str:
    return f"{GOOGLE_PLACE_DETAILS_LOCK_KEY_PREFIX}:{place_id}"


def acquire_place_details_lock(
    place_id: str,
    *,
    ttl_seconds: int = DEFAULT_GOOGLE_PLACE_DETAILS_LOCK_TTL_SECONDS,
) -> GooglePlaceDetailsLock | None:
    """
    Try to acquire Redis lock for Google Place Details fetch.
    Returns lock object when acquired, otherwise None.
    """
    if not place_id:
        return None

    redis = get_redis_connection("default")
    token = str(uuid.uuid4())
    key = _build_place_details_lock_key(place_id)

    acquired = redis.set(key, token, nx=True, ex=ttl_seconds)
    if not acquired:
        return None

    return GooglePlaceDetailsLock(key=key, token=token)


def release_place_details_lock(lock: GooglePlaceDetailsLock | None) -> None:
    """
    Release lock only if token still matches.
    """
    if not lock:
        return

    redis = get_redis_connection("default")

    lua_script = """
    if redis.call("GET", KEYS[1]) == ARGV[1] then
        return redis.call("DEL", KEYS[1])
    end
    return 0
    """
    redis.eval(lua_script, 1, lock.key, lock.token)


def wait_for_place_details_cache(
    place_id: str,
    *,
    attempts: int,
    sleep_seconds: float,
    cache_getter,
):
    """
    Poll cache for place details while another worker holds the lock.
    """
    if not place_id or attempts <= 0:
        return None

    for _ in range(attempts):
        time.sleep(sleep_seconds)
        cached = cache_getter(place_id)
        if cached:
            return cached

    return None