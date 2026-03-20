from django.core.paginator import Paginator
from django.shortcuts import render

from .services.dealer_service import search_dealers


def home_view(request):
    return render(request, "dealers/home.html")


def search_view(request):
    city = request.GET.get("city")
    radius = request.GET.get("radius", "10")
    min_rating = request.GET.get("min_rating")
    sort = request.GET.get("sort", "score")
    page_number = request.GET.get("page", 1)

    dealers = []

    if city:
        dealers = search_dealers(city=city, radius=radius)

        if min_rating:
            try:
                min_rating_value = float(min_rating)
                dealers = [d for d in dealers if (d.get("rating") or 0) >= min_rating_value]
            except ValueError:
                pass

        if sort == "rating":
            dealers = sorted(dealers, key=lambda x: x.get("rating") or 0, reverse=True)
        elif sort == "reviews":
            dealers = sorted(dealers, key=lambda x: x.get("reviews") or 0, reverse=True)

    paginator = Paginator(dealers, 15)
    page_obj = paginator.get_page(page_number)

    context = {
        "dealers": page_obj,
        "page_obj": page_obj,
        "city": city,
        "radius": radius,
        "min_rating": min_rating,
        "sort": sort,
        "total": len(dealers),
    }
    return render(request, "dealers/search.html", context)