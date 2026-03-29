def _get_client_ip(request) -> str:
    """Return real client IP, respecting X-Forwarded-For when present."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")