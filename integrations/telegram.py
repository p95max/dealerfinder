import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_telegram_message(text: str) -> None:
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        logger.warning("Telegram bot token or chat id is not configured.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
            },
            timeout=5,
        ).raise_for_status()
    except requests.RequestException:
        logger.exception("Failed to send Telegram notification.")