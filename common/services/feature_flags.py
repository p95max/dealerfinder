from __future__ import annotations

from django.core.cache import cache


FEATURE_KEY_PREFIX = "feature"


def _build_feature_key(name: str) -> str:
    return f"{FEATURE_KEY_PREFIX}:{name}"


def is_feature_enabled(name: str, default: bool = False) -> bool:
    value = cache.get(_build_feature_key(name))

    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on", "enabled"}

    if isinstance(value, int):
        return value == 1

    return default


def set_feature_flag(name: str, enabled: bool, timeout: int | None = None) -> None:
    cache.set(_build_feature_key(name), enabled, timeout=timeout)


def delete_feature_flag(name: str) -> None:
    cache.delete(_build_feature_key(name))