import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_telegram_message(text: str, context: dict | None = None) -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        logger.warning("Telegram config missing")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
            },
            timeout=5,
        )
        response.raise_for_status()

    except requests.RequestException:
        logger.exception(
            "Telegram send failed",
            extra=context or {}
        )