import requests
from django.conf import settings


def search_places(city, radius):
    url = "https://places.googleapis.com/v1/places:searchText"

    headers = {
        "X-Goog-Api-Key": settings.GOOGLE_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.location,places.rating,places.userRatingCount"
    }

    payload = {
        "textQuery": f"car dealer in {city}",
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()

    return response.json()