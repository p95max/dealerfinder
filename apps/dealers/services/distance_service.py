import math


EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return distance in kilometers between two geo points."""
    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)

    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS_KM * c


def attach_distance_to_dealers(
    dealers: list[dict],
    user_lat: float,
    user_lng: float,
) -> list[dict]:
    enriched = []

    for dealer in dealers:
        lat = dealer.get("lat")
        lng = dealer.get("lng")

        dealer_copy = dealer.copy()

        if lat is None or lng is None:
            dealer_copy["distance_km"] = None
        else:
            dealer_copy["distance_km"] = round(
                haversine_km(user_lat, user_lng, lat, lng),
                1,
            )

        enriched.append(dealer_copy)

    return enriched