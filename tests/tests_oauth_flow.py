import pytest
from django.contrib.messages import get_messages
from django.urls import reverse


@pytest.mark.django_db
class OAuthFlowTests:
    def test_google_oauth_start_without_turnstile_redirects_to_login(self, client, mocker):
        mocked_verify = mocker.patch(
            "apps.users.views.verify_turnstile",
            return_value=False,
        )

        response = client.post(
            reverse("users:google_oauth_start"),
            data={"cf-turnstile-response": ""},
            REMOTE_ADDR="127.0.0.1",
            follow=True,
        )

        assert response.status_code == 200
        assert response.redirect_chain[0][0].endswith(reverse("account_login"))

        messages = [message.message for message in get_messages(response.wsgi_request)]
        assert "Please complete the security check." in messages

        mocked_verify.assert_called_once_with("", "127.0.0.1")

        session = client.session
        assert session.get("google_oauth_verified") is None

    def test_google_oauth_start_with_valid_turnstile_redirects_to_google_login(self, client, mocker):
        mocked_verify = mocker.patch(
            "apps.users.views.verify_turnstile",
            return_value=True,
        )

        response = client.post(
            reverse("users:google_oauth_start"),
            data={"cf-turnstile-response": "token-ok"},
            REMOTE_ADDR="127.0.0.1",
        )

        assert response.status_code == 302
        assert response.url == reverse("google_login")

        mocked_verify.assert_called_once_with("token-ok", "127.0.0.1")

        session = client.session
        assert session["google_oauth_verified"] is True

    def test_direct_google_login_without_session_flag_redirects_to_account_login(self, client):
        response = client.get(reverse("google_login"))

        assert response.status_code == 302
        assert response.url == reverse("account_login")

        session = client.session
        assert session.get("google_oauth_verified") is None