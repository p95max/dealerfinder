import requests
from django.conf import settings

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def verify_turnstile(token: str, remote_ip: str = None) -> bool:
    """Verify Cloudflare Turnstile token. Returns True if valid."""
    if not token:
        return False

    data = {
        "secret": settings.TURNSTILE_SECRET_KEY,
        "response": token,
    }
    if remote_ip:
        data["remoteip"] = remote_ip

    try:
        response = requests.post(SITEVERIFY_URL, data=data, timeout=10)
        response.raise_for_status()
        return response.json().get("success", False)
    except requests.RequestException:
        return False