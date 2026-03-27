import pytest
from unittest.mock import patch

from apps.dealers.models import SearchCache
from apps.dealers.services.dealer_service import build_query_key, search_dealers


@pytest.mark.django_db
class DealerServiceTests:
    def test_search_dealers_returns_cached_data_on_cache_hit(self):
        city = "Berlin"
        radius = "10"
        query_key = build_query_key(city, radius)

        cached_results = [
            {
                "place_id": "cached-1",
                "name": "Cached Autohaus",
                "address": "Cached street 1",
                "lat": 52.52,
                "lng": 13.40,
                "rating": 4.7,
                "reviews": 120,
                "phone": "+49123456789",
                "website": "https://cached.example.com",
                "open_now": True,
                "has_weekend": True,
            }
        ]
        SearchCache.objects.create(query_key=query_key, results_json=cached_results)

        with patch("apps.dealers.services.dealer_service.search_all_places") as mocked_google:
            dealers, from_cache = search_dealers(city=city, radius=radius)

        assert from_cache is True
        assert dealers == cached_results
        mocked_google.assert_not_called()

    def test_search_dealers_calls_google_and_saves_cache_on_cache_miss(self):
        city = "Berlin"
        radius = "10"
        query_key = build_query_key(city, radius)

        raw_google_response = {
            "places": [
                {
                    "id": "place-low",
                    "displayName": {"text": "Low score dealer"},
                    "formattedAddress": "Low street 1",
                    "location": {"latitude": 52.50, "longitude": 13.37},
                    "rating": 4.9,
                    "userRatingCount": 1,
                    "nationalPhoneNumber": "+49111111111",
                    "websiteUri": "https://low.example.com",
                    "currentOpeningHours": {"openNow": True},
                    "regularOpeningHours": {
                        "weekdayDescriptions": [
                            "Monday: 09:00-18:00",
                        ]
                    },
                },
                {
                    "id": "place-high",
                    "displayName": {"text": "High score dealer"},
                    "formattedAddress": "High street 2",
                    "location": {"latitude": 52.51, "longitude": 13.38},
                    "rating": 4.6,
                    "userRatingCount": 300,
                    "nationalPhoneNumber": "+49222222222",
                    "websiteUri": "https://high.example.com",
                    "currentOpeningHours": {"openNow": False},
                    "regularOpeningHours": {
                        "weekdayDescriptions": [
                            "Saturday: 10:00-14:00",
                        ]
                    },
                },
            ]
        }

        with patch(
            "apps.dealers.services.dealer_service.search_all_places",
            return_value=raw_google_response,
        ) as mocked_google:
            dealers, from_cache = search_dealers(city=city, radius=radius)

        assert from_cache is False
        mocked_google.assert_called_once_with(city=city, radius=radius)

        assert len(dealers) == 2

        # Sorted by score: rating * log1p(reviews)
        assert dealers[0]["place_id"] == "place-high"
        assert dealers[0]["name"] == "High score dealer"
        assert dealers[0]["address"] == "High street 2"
        assert dealers[0]["lat"] == 52.51
        assert dealers[0]["lng"] == 13.38
        assert dealers[0]["rating"] == 4.6
        assert dealers[0]["reviews"] == 300
        assert dealers[0]["phone"] == "+49222222222"
        assert dealers[0]["website"] == "https://high.example.com"
        assert dealers[0]["open_now"] is False
        assert dealers[0]["has_weekend"] is True

        assert dealers[1]["place_id"] == "place-low"
        assert dealers[1]["has_weekend"] is False

        cache = SearchCache.objects.get(query_key=query_key)
        assert cache.results_json == dealers