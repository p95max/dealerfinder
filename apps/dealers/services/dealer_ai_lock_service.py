import uuid
from dataclasses import dataclass

from django_redis import get_redis_connection


LOCK_KEY_PREFIX = "lock:ai_summary"
DEFAULT_LOCK_TTL_SECONDS = 60


@dataclass(frozen=True)
class DealerAiLock:
    key: str
    token: str


def _build_lock_key(place_id: str) -> str:
    return f"{LOCK_KEY_PREFIX}:{place_id}"


def acquire_ai_summary_lock(
    place_id: str,
    *,
    ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
) -> DealerAiLock | None:
    """
    Try to acquire a Redis deduplication lock for dealer AI summary generation.
    Returns lock object if acquired, otherwise None.
    """
    if not place_id:
        return None

    redis = get_redis_connection("default")
    token = str(uuid.uuid4())
    key = _build_lock_key(place_id)

    acquired = redis.set(key, token, nx=True, ex=ttl_seconds)
    if not acquired:
        return None

    return DealerAiLock(key=key, token=token)


def release_ai_summary_lock(lock: DealerAiLock | None) -> None:
    """
    Release lock only if current token still owns it.
    Protects against deleting someone else's lock after TTL refresh/race.
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