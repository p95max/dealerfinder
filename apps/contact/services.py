import logging

from integrations.email_notifications import send_contact_fallback_email
from integrations.telegram import send_telegram_message

logger = logging.getLogger(__name__)


def notify_new_contact_message(contact_message) -> None:
    context = {
        "event": "contact_notification",
        "contact_email": contact_message.email,
    }

    telegram_text = (
        "📩 <b>New Contact Message</b>\n\n"
        f"👤 <b>Name:</b> {contact_message.name}\n"
        f"✉️ <b>Email:</b> {contact_message.email}\n"
        f"💬 <b>Message:</b>\n{contact_message.message[:500]}"
    )

    telegram_sent = send_telegram_message(telegram_text, context=context)

    if telegram_sent:
        return

    logger.warning(
        "Telegram notification failed, sending fallback email",
        extra={
            "event": "contact_notification_fallback_triggered",
            "contact_email": contact_message.email,
        },
    )

    email_subject = f"New contact message from {contact_message.name}"
    email_body = (
        "A new contact form message was received.\n\n"
        f"Name: {contact_message.name}\n"
        f"Email: {contact_message.email}\n\n"
        f"Message:\n{contact_message.message}\n"
    )

    send_contact_fallback_email(
        subject=email_subject,
        message=email_body,
        context={
            "event": "contact_notification_email_fallback",
            "contact_email": contact_message.email,
        },
    )