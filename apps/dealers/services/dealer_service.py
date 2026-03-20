from .cache_service import get_cache, set_cache
from .google_places import search_places


def build_query_key(city, radius):
    return f"{city}_{radius}"


def normalize(data):
    results = []

    for p in data.get("places", []):
        results.append({
            "name": p.get("displayName", {}).get("text"),
            "lat": p.get("location", {}).get("latitude"),
            "lng": p.get("location", {}).get("longitude"),
            "rating": p.get("rating"),
            "reviews": p.get("userRatingCount"),
        })

    return results


def search_dealers(city, radius):
    key = build_query_key(city, radius)

    cached = get_cache(key)
    if cached:
        return cached

    raw = search_places(city, radius)
    normalized = normalize(raw)

    set_cache(key, normalized)

    return normalized