import requests

from django.conf import settings


TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


MAX_PAGES = 3

def search_places(city: str, radius: int | str, page_token: str = None):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_API_KEY,
        "X-Goog-FieldMask": ",".join([
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
        ]),
    }

    payload = {
        "textQuery": f"car dealer in {city}, Germany",
        "maxResultCount": 20,
        "locationRestriction": {
            "rectangle": {
                "low": {"latitude": 47.27, "longitude": 5.87},
                "high": {"latitude": 55.06, "longitude": 15.04},
            }
        },
    }

    if page_token:
        payload["pageToken"] = page_token

    response = requests.post(TEXT_SEARCH_URL, json=payload, headers=headers, timeout=20)
    response.raise_for_status()
    return response.json()


def search_all_places(city: str, radius: int | str):
    all_places = []
    page_token = None

    for _ in range(MAX_PAGES):
        data = search_places(city, radius, page_token)
        all_places.extend(data.get("places", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return {"places": all_places}