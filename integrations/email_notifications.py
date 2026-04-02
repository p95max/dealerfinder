import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_contact_fallback_email(
    subject: str,
    message: str,
    context: dict | None = None,
) -> bool:
    recipient = settings.CONTACT_FALLBACK_EMAIL

    if not recipient:
        logger.warning(
            "Contact fallback email is not configured",
            extra={
                "event": "contact_fallback_email_missing",
            },
        )
        return False

    safe_context = {
        "event": None,
    }

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )

        logger.info(
            "Contact fallback email sent",
            extra={
                "event": "contact_fallback_email_sent",
                "recipient": recipient,
                "subject": subject,
            },
        )

        return True

    except Exception:
        logger.exception(
            "Contact fallback email send failed",
            extra={
                "event": "contact_fallback_email_failed",
                "recipient": recipient,
                "subject": subject,
            },
        )
        return False