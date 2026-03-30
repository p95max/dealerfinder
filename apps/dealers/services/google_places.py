import requests

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .geocoding_service import geocode_city


TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
MAX_PAGES = 3
GOOGLE_CAP_CACHE_KEY = "google_api_calls_today"


def _get_google_calls_today() -> int:
    return cache.get(GOOGLE_CAP_CACHE_KEY, 0)


def _increment_google_calls():
    try:
        cache.incr(GOOGLE_CAP_CACHE_KEY)
    except ValueError:
        import datetime
        now = timezone.localtime()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        seconds_until_midnight = int((midnight - now).total_seconds())
        cache.set(GOOGLE_CAP_CACHE_KEY, 1, timeout=seconds_until_midnight)


def is_google_cap_reached() -> bool:
    return _get_google_calls_today() >= settings.MAX_GOOGLE_CALLS_PER_DAY


def search_places(city: str, radius: int | str, page_token: str = None):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_API_KEY,
        "X-Goog-FieldMask": ",".join([
            "places.id",
            "places.displayName",
            "places.formattedAddress",
            "places.location",
            "places.rating",
            "places.userRatingCount",
            "places.currentOpeningHours.openNow",
            "places.regularOpeningHours.weekdayDescriptions",
            "places.nationalPhoneNumber",
            "places.websiteUri",
            "nextPageToken",
        ]),
    }

    try:
        radius_m = int(float(radius or 20)) * 1000
    except (TypeError, ValueError):
        radius_m = 20_000

    geo = geocode_city(city)

    if geo:
        location_bias = {
            "circle": {
                "center": {"latitude": geo["lat"], "longitude": geo["lng"]},
                "radius": float(radius_m),
            }
        }
        payload = {
            "textQuery": f"car dealer in {city}, Germany",
            "maxResultCount": 20,
            "locationBias": location_bias,
        }
    else:
        payload = {
            "textQuery": f"car dealer in {city}, Germany",
            "maxResultCount": 20,
            "locationRestriction": {
                "rectangle": {
                    "low": {"latitude": 47.27, "longitude": 5.87},
                    "high": {"latitude": 55.06, "longitude": 15.04},
                }
            },
        }

    if page_token:
        payload["pageToken"] = page_token

    _increment_google_calls()
    response = requests.post(TEXT_SEARCH_URL, json=payload, headers=headers, timeout=20)

    # print("Google API status:", response.status_code)
    # print("Google API response:", response.text)

    response.raise_for_status()
    return response.json()


def search_all_places(city: str, radius: int | str):
    all_places = []
    page_token = None

    for _ in range(MAX_PAGES):
        data = search_places(city, radius, page_token)
        all_places.extend(data.get("places", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return {"places": all_places}