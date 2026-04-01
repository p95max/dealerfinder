from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from integrations.google_oauth import GoogleOAuthAdapter

User = get_user_model()


def make_user(**kwargs):
    defaults = dict(
        username="testuser",
        email="test@example.com",
        password="pass",
        plan="free",
        daily_quota=30,
        terms_accepted=True,  # prevent LoginGateMiddleware redirect
    )
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


# ---------------------------------------------------------------------------
# delete_account_view
# ---------------------------------------------------------------------------

class DeleteAccountViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("users:delete_account")

    def _login(self, user):
        self.client.force_login(user)

    @patch("apps.users.views.verify_turnstile", return_value=True)
    def test_delete_removes_user_and_redirects(self, _mock):
        user = make_user()
        self._login(user)
        user_pk = user.pk

        response = self.client.post(self.url, {"cf-turnstile-response": "token"})

        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertFalse(User.objects.filter(pk=user_pk).exists())

    @patch("apps.users.views.verify_turnstile", return_value=True)
    def test_delete_cascades_favorites(self, _mock):
        from apps.users.models import Favorite
        user = make_user()
        Favorite.objects.create(user=user, place_id="abc", name="Test Dealer")
        self._login(user)
        user_pk = user.pk

        self.client.post(self.url, {"cf-turnstile-response": "token"})

        self.assertFalse(User.objects.filter(pk=user_pk).exists())
        self.assertFalse(Favorite.objects.filter(user_id=user_pk).exists())

    @patch("apps.users.views.verify_turnstile", return_value=False)
    def test_invalid_turnstile_does_not_delete(self, _mock):
        user = make_user()
        self._login(user)
        user_pk = user.pk

        response = self.client.post(self.url, {"cf-turnstile-response": "bad"})

        self.assertRedirects(response, reverse("users:profile"), fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(pk=user_pk).exists())

    def test_get_request_redirects_without_deleting(self):
        user = make_user()
        self._login(user)
        user_pk = user.pk

        response = self.client.get(self.url)

        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(pk=user_pk).exists())

    def test_unauthenticated_user_redirected(self):
        response = self.client.post(self.url, {"cf-turnstile-response": "token"})
        self.assertEqual(response.status_code, 302)


# ---------------------------------------------------------------------------
# GoogleOAuthAdapter
# ---------------------------------------------------------------------------

def _make_sociallogin(sub="google-sub-123", existing_plan=None, existing_quota=None):
    user = MagicMock()
    user.plan = existing_plan or ""
    user.daily_quota = existing_quota or 0

    account = MagicMock()
    account.extra_data = {"sub": sub}

    sociallogin = MagicMock()
    sociallogin.account = account

    return user, sociallogin


class GoogleOAuthAdapterTests(TestCase):
    def setUp(self):
        self.adapter = GoogleOAuthAdapter()
        self.request = MagicMock()

    def _call_save_user(self, user, sociallogin):
        with patch.object(
            GoogleOAuthAdapter.__bases__[0],
            "save_user",
            return_value=user,
        ):
            return self.adapter.save_user(self.request, sociallogin)

    def test_new_user_gets_free_plan(self):
        user, sociallogin = _make_sociallogin(existing_plan="")
        result = self._call_save_user(user, sociallogin)
        self.assertEqual(result.plan, "free")

    def test_new_user_gets_free_daily_quota(self):
        from django.conf import settings
        user, sociallogin = _make_sociallogin(existing_plan="")
        result = self._call_save_user(user, sociallogin)
        self.assertEqual(result.daily_quota, settings.FREE_DAILY_LIMIT)

    def test_new_user_google_sub_is_set(self):
        user, sociallogin = _make_sociallogin(sub="sub-xyz")
        result = self._call_save_user(user, sociallogin)
        self.assertEqual(result.google_sub, "sub-xyz")

    def test_existing_premium_plan_not_overwritten(self):
        user, sociallogin = _make_sociallogin(existing_plan="premium", existing_quota=200)
        result = self._call_save_user(user, sociallogin)
        self.assertEqual(result.plan, "premium")
        self.assertEqual(result.daily_quota, 200)

    def test_anon_plan_upgraded_to_free(self):
        user, sociallogin = _make_sociallogin(existing_plan="anon")
        result = self._call_save_user(user, sociallogin)
        self.assertEqual(result.plan, "free")