import pytest
from django.contrib.messages import get_messages
from django.core.cache import cache
from django.urls import reverse

from apps.contact.models import ContactMessage


@pytest.mark.django_db
class ContactViewTests:
    def setup_method(self):
        cache.clear()

    def test_contact_view_get_returns_200(self, client):
        response = client.get(reverse("contact:contact"))

        assert response.status_code == 200

    def test_contact_view_successful_post_saves_message_and_redirects(self, client, mocker):
        mocker.patch("apps.contact.views.verify_turnstile", return_value=True)
        mocker.patch("apps.contact.views.notify_new_contact_message")

        response = client.post(
            reverse("contact:contact"),
            data={
                "name": "Max",
                "email": "max@example.com",
                "message": "Hello from test",
                "cf-turnstile-response": "token-ok",
            },
            REMOTE_ADDR="127.0.0.1",
        )

        assert response.status_code == 302
        assert response.url == reverse("contact:contact")

        assert ContactMessage.objects.count() == 1
        msg = ContactMessage.objects.get()
        assert msg.name == "Max"
        assert msg.email == "max@example.com"
        assert msg.message == "Hello from test"

    def test_contact_view_successful_post_sets_success_message(self, client, mocker):
        mocker.patch("apps.contact.views.verify_turnstile", return_value=True)
        mocker.patch("apps.contact.views.notify_new_contact_message")

        response = client.post(
            reverse("contact:contact"),
            data={
                "name": "Max",
                "email": "max@example.com",
                "message": "Hello from test",
                "cf-turnstile-response": "token-ok",
            },
            REMOTE_ADDR="127.0.0.1",
            follow=True,
        )

        msgs = [m.message for m in get_messages(response.wsgi_request)]
        assert "Your message has been sent. We'll get back to you soon." in msgs
        assert ContactMessage.objects.count() == 1

    def test_contact_view_incomplete_data_returns_warning_and_does_not_save(self, client, mocker):
        mocked_verify = mocker.patch("apps.contact.views.verify_turnstile")

        response = client.post(
            reverse("contact:contact"),
            data={
                "name": "Max",
                "email": "",
                "message": "Hello from test",
                "cf-turnstile-response": "token-ok",
            },
            REMOTE_ADDR="127.0.0.1",
            follow=True,
        )

        assert response.status_code == 200
        assert ContactMessage.objects.count() == 0

        msgs = [m.message for m in get_messages(response.wsgi_request)]
        assert "Please correct the form and fill in all required fields." in msgs

        mocked_verify.assert_not_called()

    def test_contact_view_invalid_email_returns_error_and_does_not_save(self, client, mocker):
        mocked_verify = mocker.patch("apps.contact.views.verify_turnstile")

        response = client.post(
            reverse("contact:contact"),
            data={
                "name": "Max",
                "email": "not-an-email",
                "message": "Hello from test",
                "cf-turnstile-response": "token-ok",
            },
            REMOTE_ADDR="127.0.0.1",
            follow=True,
        )

        assert response.status_code == 200
        assert ContactMessage.objects.count() == 0
        mocked_verify.assert_not_called()

    def test_contact_view_returns_429_when_rate_limit_exceeded(self, client, mocker):
        mocker.patch("apps.contact.views.verify_turnstile", return_value=True)
        mocker.patch("apps.contact.views.notify_new_contact_message")

        for _ in range(3):
            client.post(
                reverse("contact:contact"),
                data={
                    "name": "Max",
                    "email": "max@example.com",
                    "message": "Hello from test",
                    "cf-turnstile-response": "token-ok",
                },
                REMOTE_ADDR="127.0.0.1",
            )

        response = client.post(
            reverse("contact:contact"),
            data={
                "name": "Max",
                "email": "max@example.com",
                "message": "Hello from test",
                "cf-turnstile-response": "token-ok",
            },
            REMOTE_ADDR="127.0.0.1",
        )

        assert response.status_code == 429