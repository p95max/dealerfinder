import time
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings

from apps.users.middleware import ThrottleMiddleware


def make_search_request(factory, city="Berlin"):
    """Helper — GET /search/?city=Berlin with resolver_match stubbed."""
    request = factory.get("/search/", {"city": city})
    match = MagicMock()
    match.url_name = "search"
    match.app_name = "dealers"
    request.resolver_match = match
    request.session = {}
    return request


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
        """Two different authenticated users on same IP should have separate rate buckets."""
        middleware = self._make_middleware(rate=2)

        for pk in [1, 2]:
            for _ in range(2):
                request = make_search_request(self.factory)
                request.user = self._make_user(pk=pk)
                request.META["REMOTE_ADDR"] = "1.2.3.4"
                response = middleware(request)
                self.assertNotEqual(response.status_code, 429)

    def test_throttle_by_ip_for_anon(self):
        """Anonymous users are throttled by IP."""
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
        """After the time window changes, throttle resets because a new cache key is used."""
        middleware = self._make_middleware(rate=2)
        user = self._make_user()

        for _ in range(2):
            request = make_search_request(self.factory)
            request.user = user
            request.META["REMOTE_ADDR"] = "1.2.3.4"
            middleware(request)

        with patch("apps.users.middleware.time.time", return_value=time.time() + 61):
            request = make_search_request(self.factory)
            request.user = user
            request.META["REMOTE_ADDR"] = "1.2.3.4"
            response = middleware(request)

        self.assertNotEqual(response.status_code, 429)

    @override_settings(TRUST_X_FORWARDED_FOR=False)
    def test_remote_addr_used_when_forwarded_for_not_trusted(self):
        """
        When TRUST_X_FORWARDED_FOR is disabled, REMOTE_ADDR must be used.
        Requests with different X-Forwarded-For but same REMOTE_ADDR hit one bucket.
        """
        middleware = self._make_middleware(rate=1)
        user = MagicMock(is_authenticated=False)

        request = make_search_request(self.factory)
        request.user = user
        request.META["HTTP_X_FORWARDED_FOR"] = "5.5.5.5, 10.0.0.1"
        request.META["REMOTE_ADDR"] = "10.0.0.1"
        middleware(request)

        request2 = make_search_request(self.factory)
        request2.user = user
        request2.META["HTTP_X_FORWARDED_FOR"] = "6.6.6.6, 10.0.0.1"
        request2.META["REMOTE_ADDR"] = "10.0.0.1"
        response = middleware(request2)

        self.assertEqual(response.status_code, 429)

    @override_settings(TRUST_X_FORWARDED_FOR=True)
    def test_x_forwarded_for_used_when_trusted(self):
        """
        When TRUST_X_FORWARDED_FOR is enabled, the first forwarded IP must be used.
        Same forwarded IP should hit the same throttle bucket.
        """
        middleware = self._make_middleware(rate=1)
        user = MagicMock(is_authenticated=False)

        request = make_search_request(self.factory)
        request.user = user
        request.META["HTTP_X_FORWARDED_FOR"] = "5.5.5.5, 10.0.0.1"
        request.META["HTTP_X_REAL_IP"] = "10.0.0.1"
        request.META["REMOTE_ADDR"] = "10.0.0.1"
        middleware(request)

        request2 = make_search_request(self.factory)
        request2.user = user
        request2.META["HTTP_X_FORWARDED_FOR"] = "5.5.5.5, 10.0.0.2"
        request2.META["HTTP_X_REAL_IP"] = "10.0.0.2"
        request2.META["REMOTE_ADDR"] = "10.0.0.2"
        response = middleware(request2)

        self.assertEqual(response.status_code, 429)

    def test_non_search_request_is_ignored(self):
        middleware = self._make_middleware(rate=1)

        request = self.factory.get("/")
        request.user = MagicMock(is_authenticated=False)
        request.session = {}
        request.resolver_match = MagicMock(url_name="home", app_name="core")
        request.META["REMOTE_ADDR"] = "1.2.3.4"

        response = middleware(request)

        self.assertEqual(response.status_code, 200)