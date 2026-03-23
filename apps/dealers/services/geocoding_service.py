import requests
from django.conf import settings
from django.core.cache import cache

GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
CACHE_PREFIX = "geocode:"
CACHE_TTL = 60 * 60 * 24 * 30  # 30 days


def geocode_city(city: str) -> dict | None:
    """
    Returns {"lat": float, "lng": float, "country_code": str} or None if not found.
    Result is cached for 30 days.
    """
    cache_key = f"{CACHE_PREFIX}{city.lower().strip()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    response = requests.get(
        GEOCODING_URL,
        params={"address": city, "key": settings.GOOGLE_API_KEY},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    if data.get("status") != "OK" or not data.get("results"):
        return None

    result = data["results"][0]
    location = result["geometry"]["location"]

    country_code = None
    for component in result.get("address_components", []):
        if "country" in component.get("types", []):
            country_code = component.get("short_name")
            break

    geo = {
        "lat": location["lat"],
        "lng": location["lng"],
        "country_code": country_code,
    }
    cache.set(cache_key, geo, CACHE_TTL)
    return geo


def is_german_city(city: str) -> bool:
    geo = geocode_city(city)
    if not geo:
        return False
    return geo.get("country_code") == "DE"