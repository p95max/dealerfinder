from django.conf import settings


def _get_client_ip(request) -> str:
    """
    Return client IP address.

    Trust X-Forwarded-For only when explicitly enabled, e.g. behind a trusted
    reverse proxy in production.
    """
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            parts = [part.strip() for part in forwarded.split(",") if part.strip()]
            if parts:
                return parts[0]

    real_ip = request.META.get("HTTP_X_REAL_IP", "").strip()
    if real_ip:
        return real_ip

    return request.META.get("REMOTE_ADDR", "").strip()