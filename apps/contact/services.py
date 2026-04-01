from integrations.telegram import send_telegram_message

def notify_new_contact_message(contact_message) -> None:
    text = (
        "📩 <b>New Contact Message</b>\n\n"
        f"👤 <b>Name:</b> {contact_message.name}\n"
        f"✉️ <b>Email:</b> {contact_message.email}\n"
        f"💬 <b>Message:</b>\n{contact_message.message[:500]}"
    )
    send_telegram_message(text)