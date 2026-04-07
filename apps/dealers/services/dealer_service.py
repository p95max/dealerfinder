import math

from .cache_service import get_cache, set_cache
from .distance_service import attach_distance_to_dealers
from .google_places import search_all_places, is_google_cap_reached
from apps.dealers.models import Dealer, DealerAiSummary


def build_query_key(city, radius):
    city = (city or "").strip().lower()
    try:
        radius_int = int(float(radius or 20))
    except (TypeError, ValueError):
        radius_int = 20
    return f"dealers:{city}:{radius_int}"


def normalize(data):
    results = []
    for place in data.get("places", []):
        hours = place.get("regularOpeningHours", {})
        weekday_descriptions = hours.get("weekdayDescriptions", [])
        has_weekend = any(
            day for day in weekday_descriptions
            if day.startswith("Saturday") or day.startswith("Sunday")
        )
        results.append({
            "place_id": place.get("id"),
            "name": place.get("displayName", {}).get("text"),
            "address": place.get("formattedAddress"),
            "lat": place.get("location", {}).get("latitude"),
            "lng": place.get("location", {}).get("longitude"),
            "rating": place.get("rating"),
            "reviews": place.get("userRatingCount"),
            "phone": place.get("nationalPhoneNumber"),
            "website": place.get("websiteUri"),
            "open_now": place.get("currentOpeningHours", {}).get("openNow", False),
            "has_weekend": has_weekend,
        })
    return results


def search_dealers(city, radius) -> tuple[list, bool]:
    key = build_query_key(city, radius)

    cached = get_cache(key)
    if cached:
        sync_dealers_to_db(city, cached)
        return cached, True

    if is_google_cap_reached():
        return [], True

    raw = search_all_places(city=city, radius=radius)
    if not raw:
        return [], True

    normalized = normalize(raw)
    normalized = sorted(
        normalized,
        key=lambda x: (x["rating"] or 0) * math.log1p(x["reviews"] or 0),
        reverse=True,
    )
    sync_dealers_to_db(city, normalized)
    set_cache(key, normalized)
    return normalized, False


def _is_valid_lat_lng(lat, lng) -> bool:
    if lat is None or lng is None:
        return False
    return -90 <= lat <= 90 and -180 <= lng <= 180


def filter_and_sort_dealers(
    dealers: list,
    *,
    min_rating: float | None = None,
    open_now: bool = False,
    weekends: bool = False,
    has_contacts: bool = False,
    user_lat: float | None = None,
    user_lng: float | None = None,
    max_distance_km: float | None = None,
    sort: str = "score",
) -> list:
    if min_rating is not None:
        dealers = [d for d in dealers if (d.get("rating") or 0) >= min_rating]

    if open_now:
        dealers = [d for d in dealers if d.get("open_now")]

    if weekends:
        dealers = [d for d in dealers if d.get("has_weekend")]

    if has_contacts:
        dealers = [d for d in dealers if d.get("phone") or d.get("website")]

    if _is_valid_lat_lng(user_lat, user_lng):
        dealers = attach_distance_to_dealers(dealers, user_lat, user_lng)
        if max_distance_km is not None and max_distance_km > 0:
            dealers = [
                d for d in dealers
                if d.get("distance_km") is not None and d["distance_km"] <= max_distance_km
            ]

    if sort == "rating":
        dealers = sorted(dealers, key=lambda x: x.get("rating") or 0, reverse=True)
    elif sort == "reviews":
        dealers = sorted(dealers, key=lambda x: x.get("reviews") or 0, reverse=True)
    elif sort == "distance" and _is_valid_lat_lng(user_lat, user_lng):
        dealers = sorted(
            dealers,
            key=lambda x: x.get("distance_km") if x.get("distance_km") is not None else float("inf"),
        )

    return dealers


def sync_dealers_to_db(city: str, dealers: list[dict]) -> None:
    for item in dealers:
        place_id = item.get("place_id")
        name = item.get("name")

        if not place_id or not name:
            continue

        dealer, _ = Dealer.objects.update_or_create(
            google_place_id=place_id,
            defaults={
                "name": name[:255],
                "address": item.get("address") or "",
                "city": city[:100],
                "lat": item.get("lat") or 0.0,
                "lng": item.get("lng") or 0.0,
                "rating": item.get("rating"),
                "user_ratings_total": item.get("reviews") or 0,
                "website": item.get("website") or None,
                "phone": item.get("phone") or None,
            },
        )

        DealerAiSummary.objects.get_or_create(dealer=dealer)