from django.shortcuts import render
from .services.dealer_service import search_dealers


def search_view(request):
    city = request.GET.get("city")
    radius = request.GET.get("radius", 10)

    dealers = []

    if city:
        dealers = search_dealers(city, radius)

    return render(request, "dealers/search.html", {
        "dealers": dealers,
        "city": city,
    })