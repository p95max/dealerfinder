from django.conf import settings
from common.redis import redis_client


def check_user_rate_limit(user_id: int) -> bool:
    key = f"ai:rate:{user_id}"

    current = redis_client.incr(key)

    if current == 1:
        redis_client.expire(key, settings.AI_RATE_WINDOW)

    return current <= settings.AI_RATE_LIMIT



def get_user_pending(user_id: int) -> int:
    key = f"ai:pending:user:{user_id}"
    value = redis_client.get(key)
    return int(value or 0)


def increment_user_pending(user_id: int):
    key = f"ai:pending:user:{user_id}"
    redis_client.incr(key)
    redis_client.expire(key, 3600)  # safety TTL


def decrement_user_pending(user_id: int):
    key = f"ai:pending:user:{user_id}"
    redis_client.decr(key)


def check_user_pending(user_id: int) -> bool:
    return get_user_pending(user_id) < settings.AI_MAX_PENDING_PER_USER


def get_global_pending() -> int:
    key = "ai:pending:global"
    value = redis_client.get(key)
    return int(value or 0)


def increment_global_pending():
    redis_client.incr("ai:pending:global")
    redis_client.expire("ai:pending:global", 3600)


def decrement_global_pending():
    redis_client.decr("ai:pending:global")


def check_global_pending() -> bool:
    return get_global_pending() < settings.AI_MAX_GLOBAL_PENDING



def check_ai_limits(user_id: int):
    """
    Returns:
        None | "system_busy" | "too_many_pending" | "rate_limit"
    """

    if not check_global_pending():
        return "system_busy"

    if not check_user_pending(user_id):
        return "too_many_pending"

    if not check_user_rate_limit(user_id):
        return "rate_limit"

    return None