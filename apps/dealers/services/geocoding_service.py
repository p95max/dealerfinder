import requests
import logging

from django.conf import settings
from django.core.cache import cache

GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
CACHE_PREFIX = "geocode:"
CACHE_TTL = 60 * 60 * 24 * 30  # 30 days
logger = logging.getLogger(__name__)


def geocode_city(city: str) -> dict | None:
    """
    Returns {"lat": float, "lng": float, "country_code": str} or None if not found
    or when external geocoding is temporarily unavailable.
    """
    cache_key = f"{CACHE_PREFIX}{city.lower().strip()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        response = requests.get(
            GEOCODING_URL,
            params={
                "address": city,
                "components": "country:DE",
                "language": "en",
                "key": settings.GOOGLE_API_KEY,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        logger.exception(
            "Geocoding request failed",
            extra={"event": "google_geocoding_failed", "city": city},
        )
        return None

    if data.get("status") != "OK" or not data.get("results"):
        return None

    for result in data["results"]:
        location = result.get("geometry", {}).get("location", {})
        country_code = None

        for component in result.get("address_components", []):
            if "country" in component.get("types", []):
                country_code = component.get("short_name")
                break

        if country_code == "DE" and "lat" in location and "lng" in location:
            geo = {
                "lat": location["lat"],
                "lng": location["lng"],
                "country_code": country_code,
            }
            cache.set(cache_key, geo, CACHE_TTL)
            return geo

    return None


def is_german_city(city: str) -> bool:
    geo = geocode_city(city)
    if not geo:
        return False
    return geo.get("country_code") == "DE"


def reverse_geocode_city(lat: float, lng: float) -> str | None:
    cache_key = f"{CACHE_PREFIX}reverse:{lat:.4f},{lng:.4f}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        response = requests.get(
            GEOCODING_URL,
            params={"latlng": f"{lat},{lng}", "key": settings.GOOGLE_API_KEY, "language": "en"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        logger.exception(
            "Reverse geocoding request failed",
            extra={"event": "google_reverse_geocoding_failed", "lat": lat, "lng": lng},
        )
        return None

    if data.get("status") != "OK" or not data.get("results"):
        return None

    for component in data["results"][0].get("address_components", []):
        if "locality" in component.get("types", []):
            city = component["long_name"]
            cache.set(cache_key, city, CACHE_TTL)
            return city

    return None