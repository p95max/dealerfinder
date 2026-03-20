from .cache_service import get_cache, set_cache
from .google_places import search_places


def build_query_key(city, radius):
    return f"{city}_{radius}"


def normalize(data):
    results = []

    for place in data.get("places", []):
        results.append(
            {
                "place_id": place.get("id"),
                "name": place.get("displayName", {}).get("text"),
                "address": place.get("formattedAddress"),
                "lat": place.get("location", {}).get("latitude"),
                "lng": place.get("location", {}).get("longitude"),
                "rating": place.get("rating"),
                "reviews": place.get("userRatingCount"),
            }
        )

    return results


def search_dealers(city, radius):
    key = build_query_key(city, radius)

    cached = get_cache(key)
    if cached:
        return cached

    raw = search_places(city=city, radius=radius)
    normalized = normalize(raw)
    set_cache(key, normalized)

    return normalized