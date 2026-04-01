from django.contrib import messages
from django.shortcuts import redirect, render

from apps.contact.forms import ContactForm
from apps.contact.models import ContactMessage
from apps.contact.services import notify_new_contact_message
from integrations.turnstile import verify_turnstile
from utils.http import _get_client_ip


def contact_view(request):
    if request.method == "POST":
        form = ContactForm(request.POST)

        if not form.is_valid():
            messages.warning(request, "Please correct the form and fill in all required fields.")
            return render(request, "contact.html", {"form": form})

        token = request.POST.get("cf-turnstile-response", "")
        ip = _get_client_ip(request)

        if not verify_turnstile(token, ip):
            messages.warning(request, "Please complete the security check.")
            return render(request, "contact.html", {"form": form})

        contact_message = ContactMessage.objects.create(**form.cleaned_data)
        
        notify_new_contact_message(contact_message)

        messages.success(request, "Your message has been sent. We'll get back to you soon.")
        return redirect("contact:contact")

    form = ContactForm()
    return render(request, "contact.html", {"form": form})