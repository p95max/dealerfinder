import logging
import time

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .google_places_cache_service import (
    get_cached_place_details,
    set_cached_place_details,
)
from .google_places_lock_service import (
    acquire_place_details_lock,
    release_place_details_lock,
    wait_for_place_details_cache,
)


TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACE_DETAILS_URL_TEMPLATE = "https://places.googleapis.com/v1/places/{place_id}"
MAX_PAGES = 3
GOOGLE_CAP_CACHE_KEY = "google_api_calls_today"

logger = logging.getLogger(__name__)

RETRY_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 0.5


def _get_google_calls_today() -> int:
    return cache.get(GOOGLE_CAP_CACHE_KEY, 0)


def _increment_google_calls() -> None:
    try:
        cache.incr(GOOGLE_CAP_CACHE_KEY)
    except ValueError:
        import datetime

        now = timezone.localtime()
        midnight = (
            now.replace(hour=0, minute=0, second=0, microsecond=0)
            + datetime.timedelta(days=1)
        )
        seconds_until_midnight = int((midnight - now).total_seconds())
        cache.set(GOOGLE_CAP_CACHE_KEY, 1, timeout=seconds_until_midnight)


def is_google_cap_reached() -> bool:
    return _get_google_calls_today() >= settings.MAX_GOOGLE_CALLS_PER_DAY


def _request_with_retry(
    method: str,
    url: str,
    *,
    headers: dict,
    timeout: int,
    json_body: dict | None = None,
):
    last_exc = None

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json_body,
                timeout=timeout,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "Google Places request attempt failed",
                extra={
                    "event": "google_places_request_failed_attempt",
                    "attempt": attempt,
                    "method": method,
                    "url": url,
                },
            )
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY_SECONDS)

    raise last_exc


def search_places(
    city: str,
    radius: int | str,
    page_token: str | None = None,
    *,
    geo: dict | None = None,
) -> dict | None:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_API_KEY,
        "X-Goog-FieldMask": ",".join(
            [
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
            ]
        ),
    }

    try:
        radius_m = int(float(radius or 20)) * 1000
    except (TypeError, ValueError):
        radius_m = 20_000

    payload = {
        "textQuery": f"car dealer in {city}, Germany",
        "maxResultCount": 20,
    }

    if geo:
        payload["locationBias"] = {
            "circle": {
                "center": {
                    "latitude": geo["lat"],
                    "longitude": geo["lng"],
                },
                "radius": float(radius_m),
            }
        }
    else:
        payload["locationRestriction"] = {
            "rectangle": {
                "low": {"latitude": 47.27, "longitude": 5.87},
                "high": {"latitude": 55.06, "longitude": 15.04},
            }
        }

    if page_token:
        payload["pageToken"] = page_token

    try:
        _increment_google_calls()
        response = _request_with_retry(
            "POST",
            TEXT_SEARCH_URL,
            headers=headers,
            json_body=payload,
            timeout=20,
        )
        return response.json()
    except requests.RequestException:
        logger.exception(
            "Google Places search request failed",
            extra={
                "event": "google_places_search_failed",
                "city": city,
                "radius": radius_m,
            },
        )
        return None


def search_all_places(
    city: str,
    radius: int | str,
    *,
    geo: dict | None = None,
) -> dict | None:
    all_places = []
    page_token = None

    for _ in range(MAX_PAGES):
        data = search_places(
            city=city,
            radius=radius,
            page_token=page_token,
            geo=geo,
        )
        if not data:
            return None

        all_places.extend(data.get("places", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return {"places": all_places}


def get_place_details(place_id: str) -> dict | None:
    if not place_id:
        return None

    cached = get_cached_place_details(place_id)
    if cached:
        logger.info(
            "Google Place Details served from Redis cache",
            extra={
                "event": "google_place_details_cache_hit",
                "place_id": place_id,
            },
        )
        return cached

    logger.info(
        "Google Place Details Redis cache miss",
        extra={
            "event": "google_place_details_cache_miss",
            "place_id": place_id,
        },
    )

    lock = acquire_place_details_lock(
        place_id,
        ttl_seconds=settings.GOOGLE_PLACE_DETAILS_LOCK_TTL_SECONDS,
    )

    if not lock:
        logger.info(
            "Google Place Details fetch deduplicated by lock, waiting for cache",
            extra={
                "event": "google_place_details_lock_wait_started",
                "place_id": place_id,
            },
        )

        waited_cached = wait_for_place_details_cache(
            place_id,
            attempts=settings.GOOGLE_PLACE_DETAILS_LOCK_WAIT_ATTEMPTS,
            sleep_seconds=settings.GOOGLE_PLACE_DETAILS_LOCK_WAIT_SLEEP_SECONDS,
            cache_getter=get_cached_place_details,
        )

        if waited_cached:
            logger.info(
                "Google Place Details served from Redis cache after waiting on lock",
                extra={
                    "event": "google_place_details_cache_hit_after_lock_wait",
                    "place_id": place_id,
                },
            )
            return waited_cached

        logger.warning(
            "Google Place Details cache still empty after lock wait, falling back to direct fetch",
            extra={
                "event": "google_place_details_lock_wait_timeout",
                "place_id": place_id,
            },
        )

    headers = {
        "X-Goog-Api-Key": settings.GOOGLE_API_KEY,
        "X-Goog-FieldMask": ",".join(
            [
                "id",
                "displayName",
                "rating",
                "userRatingCount",
                "nationalPhoneNumber",
                "websiteUri",
                "regularOpeningHours.weekdayDescriptions",
                "currentOpeningHours.openNow",
                "types",
                "reviews",
                "priceLevel",
            ]
        ),
    }

    url = PLACE_DETAILS_URL_TEMPLATE.format(place_id=place_id)

    try:
        _increment_google_calls()
        response = _request_with_retry(
            "GET",
            url,
            headers=headers,
            timeout=20,
        )
        data = response.json()
        set_cached_place_details(place_id, data)

        logger.info(
            "Google Place Details fetched from API and cached",
            extra={
                "event": "google_place_details_fetched",
                "place_id": place_id,
            },
        )

        return data
    except requests.RequestException:
        logger.exception(
            "Google Place Details request failed",
            extra={
                "event": "google_place_details_failed",
                "place_id": place_id,
            },
        )
        return None
    finally:
        if lock:
            release_place_details_lock(lock)