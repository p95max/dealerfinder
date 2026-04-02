import requests
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def verify_turnstile(token: str, remote_ip: str = None) -> bool:
    """Verify Cloudflare Turnstile token. Returns True if valid."""
    if not token:
        logger.warning(
            "Turnstile token missing",
            extra={
                "event": "turnstile_token_missing",
                "client_ip": remote_ip,
            },
        )
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

        result = response.json()
        success = result.get("success", False)

        if not success:
            logger.warning(
                "Turnstile verification rejected",
                extra={
                    "event": "turnstile_verification_rejected",
                    "client_ip": remote_ip,
                },
            )

        return success

    except requests.RequestException:
        logger.exception(
            "Turnstile verification failed",
            extra={
                "event": "turnstile_verification_failed",
                "client_ip": remote_ip,
            },
        )
        return False