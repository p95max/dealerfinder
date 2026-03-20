from django.shortcuts import render

from .services.dealer_service import search_dealers


def home_view(request):
    return render(request, "dealers/home.html")


def search_view(request):
    city = request.GET.get("city")
    radius = request.GET.get("radius", "10")
    min_rating = request.GET.get("min_rating")

    dealers = []

    if city:
        dealers = search_dealers(city=city, radius=radius)

        if min_rating:
            try:
                min_rating_value = float(min_rating)
                dealers = [
                    dealer for dealer in dealers
                    if dealer.get("rating") is not None and dealer.get("rating") >= min_rating_value
                ]
            except ValueError:
                pass

    context = {
        "dealers": dealers,
        "city": city,
        "radius": radius,
        "min_rating": min_rating,
    }
    return render(request, "dealers/search.html", context)