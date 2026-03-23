from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render

from .services.dealer_service import search_dealers
from .services.geocoding_service import is_german_city

DEALERS_PER_PAGE = 20


def home_view(request):
    return render(request, "home.html")


def about_view(request):
    return render(request, "about.html")


def search_view(request):
    city = request.GET.get("city")
    radius = request.GET.get("radius", "10")
    min_rating = request.GET.get("min_rating")
    sort = request.GET.get("sort", "score")
    open_now = request.GET.get("open_now")
    weekends = request.GET.get("weekends")
    has_contacts = request.GET.get("has_contacts")
    page_number = request.GET.get("page", 1)

    dealers = []

    if getattr(request, "quota_exceeded", False):
        messages.warning(request, "Daily search limit reached. Upgrade for more searches.")
        return render(request, "dealers/search.html", {
            "dealers": [],
            "quota_exceeded": True,
            "city": city,
            "radius": radius,
        })

    if city:
        dealers, from_cache = search_dealers(city=city, radius=radius)
        request.cache_hit = from_cache

        if not is_german_city(city):
            messages.warning(request, "Please enter a city located in Germany.")
            return render(request, "dealers/search.html", {
                "dealers": [], "city": city, "radius": radius,
            })

        dealers, from_cache = search_dealers(city=city, radius=radius)

        if not dealers:
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

        if sort == "rating":
            dealers = sorted(dealers, key=lambda x: x.get("rating") or 0, reverse=True)
        elif sort == "reviews":
            dealers = sorted(dealers, key=lambda x: x.get("reviews") or 0, reverse=True)

    paginator = Paginator(dealers, DEALERS_PER_PAGE)
    page_obj = paginator.get_page(page_number)

    context = {
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
    }
    return render(request, "dealers/search.html", context)