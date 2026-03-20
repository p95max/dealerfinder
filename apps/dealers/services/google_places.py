import requests

from django.conf import settings


TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


def search_places(city: str, radius: int | str):
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
            ]
        ),
    }

    payload = {
        "textQuery": f"car dealer in {city}",
        "maxResultCount": 20,
    }

    response = requests.post(TEXT_SEARCH_URL, json=payload, headers=headers, timeout=20)
    response.raise_for_status()
    return response.json()