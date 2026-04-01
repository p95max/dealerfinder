import time
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import RequestFactory, TestCase
from apps.users.middleware import reset_quota_if_new_day

from apps.users.middleware import QuotaMiddleware, ThrottleMiddleware

User = get_user_model()


def make_search_request(factory, city="Berlin"):
    """Helper — GET /search/?city=Berlin with resolver_match stubbed."""
    request = factory.get("/search/", {"city": city})
    match = MagicMock()
    match.url_name = "search"
    match.app_name = "dealers"
    request.resolver_match = match
    request.session = {}
    return request


class QuotaMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = MagicMock(return_value=MagicMock(status_code=200))
        self.middleware = QuotaMiddleware(self.get_response)

    def _make_user(self, used_today=0, daily_quota=30, last_quota_reset=None):
        user = User.objects.create_user(
            username=f"user_{User.objects.count()}",
            email=f"user{User.objects.count()}@test.com",
            password="pass",
            used_today=used_today,
            daily_quota=daily_quota,
            last_quota_reset=last_quota_reset or date.today(),
        )
        return user

    def test_quota_increments_on_cache_miss(self):
        user = self._make_user(used_today=0)
        request = make_search_request(self.factory)
        request.user = user
        request.cache_hit = False

        self.middleware(request)

        user.refresh_from_db()
        self.assertEqual(user.used_today, 1)

    def test_quota_not_incremented_on_cache_hit(self):
        user = self._make_user(used_today=5)
        request = make_search_request(self.factory)
        request.user = user
        request.cache_hit = True

        self.middleware(request)

        user.refresh_from_db()
        self.assertEqual(user.used_today, 5)

    def test_quota_exceeded_blocks_request(self):
        user = self._make_user(used_today=30, daily_quota=30)
        request = make_search_request(self.factory)
        request.user = user
        request.cache_hit = False

        self.middleware(request)

        self.assertTrue(request.quota_exceeded)
        user.refresh_from_db()
        self.assertEqual(user.used_today, 30)

    def test_quota_resets_on_new_day(self):
        yesterday = date.today() - timedelta(days=1)
        user = self._make_user(used_today=25, daily_quota=30, last_quota_reset=yesterday)
        request = make_search_request(self.factory)
        request.user = user
        request.cache_hit = False

        self.middleware(request)

        user.refresh_from_db()
        self.assertEqual(user.last_quota_reset, date.today())
        self.assertEqual(user.used_today, 1)

    def test_quota_not_reset_same_day(self):
        user = self._make_user(used_today=10, daily_quota=30, last_quota_reset=date.today())
        request = make_search_request(self.factory)
        request.user = user
        request.cache_hit = False

        self.middleware(request)

        user.refresh_from_db()
        self.assertEqual(user.used_today, 11)

    def test_anonymous_user_not_tracked(self):
        request = make_search_request(self.factory)
        request.user = MagicMock(is_authenticated=False)
        request.cache_hit = False

        self.middleware(request)

        self.assertFalse(request.quota_exceeded)

    def test_non_search_request_ignored(self):
        user = self._make_user(used_today=0)
        request = self.factory.get("/")
        request.user = user
        request.session = {}
        request.resolver_match = MagicMock(url_name="home", app_name="dealers")

        self.middleware(request)

        user.refresh_from_db()
        self.assertEqual(user.used_today, 0)

    def test_parallel_requests_do_not_exceed_quota(self):
        """F() update is atomic — parallel requests should not bypass quota check."""
        user = self._make_user(used_today=29, daily_quota=30)

        for _ in range(3):
            request = make_search_request(self.factory)
            request.user = user
            request.cache_hit = False
            user.refresh_from_db()
            reset_quota_if_new_day(user)
            request.quota_exceeded = user.used_today >= user.daily_quota
            if not request.quota_exceeded:
                User.objects.filter(pk=user.pk).update(
                    used_today=user.used_today + 1
                )

        user.refresh_from_db()
        self.assertLessEqual(user.used_today, 30)


class ThrottleMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = MagicMock(return_value=MagicMock(status_code=200))
        cache.clear()

    def _make_middleware(self, rate=3):
        with patch("apps.users.middleware.settings") as mock_settings:
            mock_settings.SEARCH_THROTTLE_RATE = rate
            return ThrottleMiddleware(self.get_response)

    def _make_user(self, pk=1):
        return MagicMock(is_authenticated=True, pk=pk)

    def test_requests_within_rate_allowed(self):
        middleware = self._make_middleware(rate=3)
        user = self._make_user()

        for _ in range(3):
            request = make_search_request(self.factory)
            request.user = user
            request.META["REMOTE_ADDR"] = "1.2.3.4"
            response = middleware(request)
            self.assertNotEqual(response.status_code, 429)

    def test_request_exceeding_rate_blocked(self):
        middleware = self._make_middleware(rate=3)
        user = self._make_user()

        for _ in range(3):
            request = make_search_request(self.factory)
            request.user = user
            request.META["REMOTE_ADDR"] = "1.2.3.4"
            middleware(request)

        request = make_search_request(self.factory)
        request.user = user
        request.META["REMOTE_ADDR"] = "1.2.3.4"
        response = middleware(request)
        self.assertEqual(response.status_code, 429)

    def test_throttle_by_user_not_ip(self):
        """Two different users on same IP should have separate rate buckets."""
        middleware = self._make_middleware(rate=2)

        for pk in [1, 2]:
            for _ in range(2):
                request = make_search_request(self.factory)
                request.user = self._make_user(pk=pk)
                request.META["REMOTE_ADDR"] = "1.2.3.4"
                response = middleware(request)
                self.assertNotEqual(response.status_code, 429)

    def test_throttle_by_ip_for_anon(self):
        """Anonymous users throttled by IP."""
        middleware = self._make_middleware(rate=2)

        for _ in range(2):
            request = make_search_request(self.factory)
            request.user = MagicMock(is_authenticated=False)
            request.META["REMOTE_ADDR"] = "9.9.9.9"
            middleware(request)

        request = make_search_request(self.factory)
        request.user = MagicMock(is_authenticated=False)
        request.META["REMOTE_ADDR"] = "9.9.9.9"
        response = middleware(request)
        self.assertEqual(response.status_code, 429)

    def test_window_expiry_resets_throttle(self):
        """After the time window, a new window key is used — throttle resets."""
        middleware = self._make_middleware(rate=2)
        user = self._make_user()

        for _ in range(2):
            request = make_search_request(self.factory)
            request.user = user
            request.META["REMOTE_ADDR"] = "1.2.3.4"
            middleware(request)

        # Simulate next time window (61s later) — new key, fresh counter
        with patch("apps.users.middleware.time.time", return_value=time.time() + 61):
            request = make_search_request(self.factory)
            request.user = user
            request.META["REMOTE_ADDR"] = "1.2.3.4"
            response = middleware(request)

        self.assertNotEqual(response.status_code, 429)

    def test_x_forwarded_for_used_for_ip(self):
        middleware = self._make_middleware(rate=1)
        user = MagicMock(is_authenticated=False)

        request = make_search_request(self.factory)
        request.user = user
        request.META["HTTP_X_FORWARDED_FOR"] = "5.5.5.5, 10.0.0.1"
        request.META["REMOTE_ADDR"] = "10.0.0.1"
        middleware(request)

        request2 = make_search_request(self.factory)
        request2.user = user
        request2.META["HTTP_X_FORWARDED_FOR"] = "5.5.5.5, 10.0.0.1"
        request2.META["REMOTE_ADDR"] = "10.0.0.1"
        response = middleware(request2)
        self.assertEqual(response.status_code, 429)