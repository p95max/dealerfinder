import re

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render

from .services.dealer_service import search_dealers
from .services.distance_service import attach_distance_to_dealers
from .services.geocoding_service import is_german_city
from .services.google_places import is_google_cap_reached


DEALERS_PER_PAGE = 20
ALLOWED_RADIUS = {1, 5, 10, 20, 30, 50, 100, 200, 300}
DEFAULT_RADIUS = 20


def home_view(request):
    return render(request, "home.html")


def about_view(request):
    return render(request, "about.html")


def _parse_float(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_valid_lat_lng(lat, lng):
    if lat is None or lng is None:
        return False
    return -90 <= lat <= 90 and -180 <= lng <= 180


def _normalize_city(city: str) -> str:
    return re.sub(r"\s+", " ", city.strip()).title()


def _is_valid_city(city: str) -> bool:
    if not city or len(city) < 2:
        return False
    if re.fullmatch(r"[\d\s\-_.,:;!?@#$%^&*()]+", city):
        return False
    return True


def _parse_radius(value) -> int:
    try:
        r = int(float(value))
        return r if r in ALLOWED_RADIUS else DEFAULT_RADIUS
    except (TypeError, ValueError):
        return DEFAULT_RADIUS


def _run_search(request, city, radius):
    dealers, from_cache = search_dealers(city=city, radius=radius)
    request.cache_hit = from_cache
    return dealers


def _search_context(city, radius, min_rating, sort, open_now, weekends, has_contacts, **extra):
    return {
        "dealers": [],
        "page_obj": [],
        "city": city,
        "radius": radius,
        "min_rating": min_rating,
        "sort": sort,
        "open_now": open_now,
        "weekends": weekends,
        "has_contacts": has_contacts,
        "total": 0,
        **extra,
    }


def search_view(request):
    if request.method == "GET" and request.GET.get("city"):
        request.session["last_search_params"] = request.GET.urlencode()
    elif request.method == "GET" and not request.GET and request.session.get("last_search_params"):
        from django.shortcuts import redirect
        return redirect(f"{request.path}?{request.session['last_search_params']}")

    city = _normalize_city(request.GET.get("city") or "")
    radius = _parse_radius(request.GET.get("radius"))
    min_rating = request.GET.get("min_rating")
    sort = request.GET.get("sort", "score")
    open_now = request.GET.get("open_now")
    weekends = request.GET.get("weekends")
    has_contacts = request.GET.get("has_contacts")
    page_number = request.GET.get("page", 1)

    user_lat = _parse_float(request.GET.get("user_lat"))
    user_lng = _parse_float(request.GET.get("user_lng"))
    max_distance_km = _parse_float(request.GET.get("max_distance_km"))

    if request.GET.get("accept_terms") and not request.user.is_authenticated:
        request.session["anon_terms"] = True

    dealers = []
    request.cache_hit = True

    ctx = lambda **extra: _search_context(
        city, radius, min_rating, sort, open_now, weekends, has_contacts, **extra
    )

    if getattr(request, "quota_exceeded", False):
        if request.user.is_authenticated:
            messages.warning(request, f"Daily search limit reached. Upgrade to Premium for {settings.PREMIUM_DAILY_LIMIT} searches/day.")
        else:
            messages.warning(request, f"Daily limit reached. Create a free account for {settings.FREE_DAILY_LIMIT} searches/day.")
        return render(request, "dealers/search.html", ctx(quota_exceeded=True))

    if city:
        if not _is_valid_city(city):
            messages.warning(request, "Please enter a valid city name.")
            return render(request, "dealers/search.html", ctx())

        if not is_german_city(city):
            messages.warning(request, "Please enter a city located in Germany.")
            return render(request, "dealers/search.html", ctx())

        dealers = _run_search(request, city, radius)

        if not dealers and is_google_cap_reached():
            messages.warning(request, "Live search is temporarily unavailable. Try a city that was searched before.")
        elif not dealers:
            messages.warning(request, "No dealers found. Please enter a city in Germany.")

        if min_rating:
            try:
                min_rating_value = float(min_rating)
                dealers = [d for d in dealers if (d.get("rating") or 0) >= min_rating_value]
            except ValueError:
                pass

        if open_now:
            dealers = [d for d in dealers if d.get("open_now")]

        if weekends:
            dealers = [d for d in dealers if d.get("has_weekend")]

        if has_contacts:
            dealers = [d for d in dealers if d.get("phone") or d.get("website")]

        if _is_valid_lat_lng(user_lat, user_lng):
            dealers = attach_distance_to_dealers(
                dealers=dealers,
                user_lat=user_lat,
                user_lng=user_lng,
            )
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

    if request.user.is_authenticated and dealers:
        favorite_place_ids = set(
            request.user.favorites.values_list("place_id", flat=True)
        )
        for dealer in dealers:
            dealer["is_favorite"] = dealer.get("place_id") in favorite_place_ids
    else:
        for dealer in dealers:
            dealer["is_favorite"] = False

    paginator = Paginator(dealers, DEALERS_PER_PAGE)
    page_obj = paginator.get_page(page_number)

    return render(request, "dealers/search.html", {
        "dealers": page_obj,
        "page_obj": page_obj,
        "city": city,
        "radius": radius,
        "min_rating": min_rating,
        "sort": sort,
        "open_now": open_now,
        "weekends": weekends,
        "has_contacts": has_contacts,
        "total": len(dealers),
    })