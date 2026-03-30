import os


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Required environment variable '{name}' is not set")
    return value


def optional_env(name: str, default: str = "") -> str:
    return os.getenv(name, default)