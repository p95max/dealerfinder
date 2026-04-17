import math

from .search_cache import get_cache, set_cache
from .distance_service import attach_distance_to_dealers, haversine_km
from .geocoding_service import geocode_city
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

    geo = geocode_city(city)

    raw = search_all_places(city=city, radius=radius, geo=geo)
    if not raw:
        return [], True

    normalized = normalize(raw)

    if geo:
        try:
            radius_km = float(radius)
            if radius_km <= 0:
                radius_km = 20.0
        except (TypeError, ValueError):
            radius_km = 20.0

        normalized = [
            item for item in normalized
            if item.get("lat") is not None
            and item.get("lng") is not None
            and haversine_km(
                geo["lat"],
                geo["lng"],
                item["lat"],
                item["lng"],
            ) <= radius_km
        ]

    normalized = sorted(
        normalized,
        key=lambda x: (
            -((x.get("rating") or 0) * math.log1p(x.get("reviews") or 0)),
            -(x.get("rating") or 0),
            -(x.get("reviews") or 0),
            x.get("place_id") or "",
        ),
    )
    sync_dealers_to_db(city, normalized)
    set_cache(key, normalized)
    return normalized, False


def _is_valid_lat_lng(lat, lng) -> bool:
    if lat is None or lng is None:
        return False
    return -90 <= lat <= 90 and -180 <= lng <= 180


def _compute_dealer_score(
    dealer: dict,
    *,
    prefer_open_now: bool = False,
    prefer_weekends: bool = False,
    prefer_contacts: bool = False,
) -> float:
    """
    Compute ranking score for a dealer.

    Base score:
    - rating adjusted by review volume

    Optional boosts:
    - open now
    - weekend availability
    - available contacts

    Boosts are intentionally small so they do not overpower the baseline quality.
    """
    rating = dealer.get("rating") or 0
    reviews = dealer.get("reviews") or 0

    score = rating * math.log1p(reviews)

    if prefer_open_now and dealer.get("open_now"):
        score += 0.35

    if prefer_weekends and dealer.get("has_weekend"):
        score += 0.25

    if prefer_contacts and (dealer.get("phone") or dealer.get("website")):
        score += 0.2

    return round(score, 4)


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
    def _score(item: dict) -> float:
        return (item.get("rating") or 0) * math.log1p(item.get("reviews") or 0)

    def _place_id(item: dict) -> str:
        return item.get("place_id") or ""

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
        dealers = sorted(
            dealers,
            key=lambda x: (
                -(x.get("rating") or 0),
                -(x.get("reviews") or 0),
                -_score(x),
                _place_id(x),
            ),
        )
    elif sort == "reviews":
        dealers = sorted(
            dealers,
            key=lambda x: (
                -(x.get("reviews") or 0),
                -(x.get("rating") or 0),
                -_score(x),
                _place_id(x),
            ),
        )
    elif sort == "distance" and _is_valid_lat_lng(user_lat, user_lng):
        dealers = sorted(
            dealers,
            key=lambda x: (
                x.get("distance_km") if x.get("distance_km") is not None else float("inf"),
                -(x.get("rating") or 0),
                -(x.get("reviews") or 0),
                _place_id(x),
            ),
        )
    else:
        # default: score
        dealers = sorted(
            dealers,
            key=lambda x: (
                -_score(x),
                -(x.get("rating") or 0),
                -(x.get("reviews") or 0),
                _place_id(x),
            ),
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