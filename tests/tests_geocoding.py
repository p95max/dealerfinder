import pytest
from unittest.mock import Mock, patch

from django.core.cache import cache

from apps.dealers.services.geocoding_service import (
    CACHE_PREFIX,
    geocode_city,
    is_german_city,
)


@pytest.mark.django_db
class GeocodingServiceTests:
    def setup_method(self):
        cache.clear()

    def test_geocode_city_returns_geo_for_valid_german_city(self):
        city = "Berlin"

        response_data = {
            "status": "OK",
            "results": [
                {
                    "geometry": {
                        "location": {
                            "lat": 52.5200,
                            "lng": 13.4050,
                        }
                    },
                    "address_components": [
                        {
                            "long_name": "Berlin",
                            "short_name": "Berlin",
                            "types": ["locality", "political"],
                        },
                        {
                            "long_name": "Germany",
                            "short_name": "DE",
                            "types": ["country", "political"],
                        },
                    ],
                }
            ],
        }

        mock_response = Mock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status.return_value = None

        with patch(
            "apps.dealers.services.geocoding_service.requests.get",
            return_value=mock_response,
        ) as mocked_get:
            result = geocode_city(city)

        assert result == {
            "lat": 52.5200,
            "lng": 13.4050,
            "country_code": "DE",
        }

        mocked_get.assert_called_once()

        cache_key = f"{CACHE_PREFIX}{city.lower().strip()}"
        assert cache.get(cache_key) == result

    def test_geocode_city_returns_none_for_invalid_city(self):
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "ZERO_RESULTS",
            "results": [],
        }
        mock_response.raise_for_status.return_value = None

        with patch(
            "apps.dealers.services.geocoding_service.requests.get",
            return_value=mock_response,
        ) as mocked_get:
            result = geocode_city("NotARealCity123")

        assert result is None
        mocked_get.assert_called_once()

    def test_is_german_city_returns_false_for_city_outside_germany(self):
        response_data = {
            "status": "OK",
            "results": [
                {
                    "geometry": {
                        "location": {
                            "lat": 48.8566,
                            "lng": 2.3522,
                        }
                    },
                    "address_components": [
                        {
                            "long_name": "Paris",
                            "short_name": "Paris",
                            "types": ["locality", "political"],
                        },
                        {
                            "long_name": "France",
                            "short_name": "FR",
                            "types": ["country", "political"],
                        },
                    ],
                }
            ],
        }

        mock_response = Mock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status.return_value = None

        with patch(
            "apps.dealers.services.geocoding_service.requests.get",
            return_value=mock_response,
        ) as mocked_get:
            result = is_german_city("Paris")

        assert result is False
        mocked_get.assert_called_once()

    def test_geocode_city_returns_cached_result_on_cache_hit(self):
        city = "Berlin"
        cache_key = f"{CACHE_PREFIX}{city.lower().strip()}"

        cached_geo = {
            "lat": 52.5200,
            "lng": 13.4050,
            "country_code": "DE",
        }

        cache.set(cache_key, cached_geo, 60)

        with patch("apps.dealers.services.geocoding_service.requests.get") as mocked_get:
            result = geocode_city(city)

        assert result == cached_geo
        mocked_get.assert_not_called()