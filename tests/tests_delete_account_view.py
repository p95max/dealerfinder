import pytest
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.urls import reverse

from apps.users.models import Favorite

User = get_user_model()


@pytest.mark.django_db
class DeleteAccountViewTests:
    def test_get_request_redirects_home(self, client):
        user = User.objects.create_user(
            email="user@example.com",
            username="user1",
            password="pass12345",
            terms_accepted=True,
        )
        client.force_login(user)

        response = client.get(reverse("users:delete_account"))

        assert response.status_code == 302
        assert response.url == reverse("home")

    def test_invalid_turnstile_redirects_to_profile_and_keeps_user(self, client, mocker):
        user = User.objects.create_user(
            email="user@example.com",
            username="user1",
            password="pass12345",
            terms_accepted=True,
        )
        client.force_login(user)

        mocked_verify = mocker.patch(
            "apps.users.views.verify_turnstile",
            return_value=False,
        )

        response = client.post(
            reverse("users:delete_account"),
            data={"cf-turnstile-response": ""},
            REMOTE_ADDR="127.0.0.1",
            follow=True,
        )

        assert response.status_code == 200
        assert User.objects.filter(pk=user.pk).exists()

        messages = [message.message for message in get_messages(response.wsgi_request)]
        assert "Please complete the security check." in messages

        mocked_verify.assert_called_once_with("", "127.0.0.1")

    def test_valid_turnstile_deletes_user_and_related_favorites(self, client, mocker):
        user = User.objects.create_user(
            email="user@example.com",
            username="user1",
            password="pass12345",
            terms_accepted=True,
        )
        Favorite.objects.create(
            user=user,
            place_id="place_1",
            name="Dealer 1",
            address="Street 1",
            city="Berlin",
        )

        client.force_login(user)

        mocked_verify = mocker.patch(
            "apps.users.views.verify_turnstile",
            return_value=True,
        )

        response = client.post(
            reverse("users:delete_account"),
            data={"cf-turnstile-response": "valid-token"},
            REMOTE_ADDR="127.0.0.1",
            follow=True,
        )

        assert response.status_code == 200
        assert not User.objects.filter(pk=user.pk).exists()
        assert not Favorite.objects.filter(place_id="place_1").exists()

        messages = [message.message for message in get_messages(response.wsgi_request)]
        assert "Your account has been deleted." in messages

        mocked_verify.assert_called_once_with("valid-token", "127.0.0.1")

        session = client.session
        assert "_auth_user_id" not in session