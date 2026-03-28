from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import redirect, render

from common.http import _get_client_ip
from .forms import ContactForm
from .models import ContactMessage
from .services.dealer_service import search_dealers
from .services.distance_service import attach_distance_to_dealers
from .services.geocoding_service import is_german_city

from integrations.turnstile import verify_turnstile


DEALERS_PER_PAGE = 20


def home_view(request):
    return render(request, "home.html")


def about_view(request):
    return render(request, "about.html")


def contact_view(request):
    if request.method == "POST":
        form = ContactForm(request.POST)

        if not form.is_valid():
            messages.warning(request, "Please correct the form and fill in all required fields.")
            return render(request, "contact.html", {"form": form})

        token = request.POST.get("cf-turnstile-response", "")
        ip = _get_client_ip(request)

        if not verify_turnstile(token, ip):
            messages.warning(request, "Please complete the security check.")
            return render(request, "contact.html", {"form": form})

        ContactMessage.objects.create(**form.cleaned_data)
        messages.success(request, "Your message has been sent. We'll get back to you soon.")
        return redirect("dealers:contact")

    form = ContactForm()
    return render(request, "contact.html", {"form": form})


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


def _run_search(request, city, radius):
    dealers, from_cache = search_dealers(city=city, radius=radius)
    request.cache_hit = from_cache
    return dealers


def search_view(request):
    city = (request.GET.get("city") or "").strip()
    radius = request.GET.get("radius", "10")
    min_rating = request.GET.get("min_rating")
    sort = request.GET.get("sort", "score")
    open_now = request.GET.get("open_now")
    weekends = request.GET.get("weekends")
    has_contacts = request.GET.get("has_contacts")
    page_number = request.GET.get("page", 1)

    user_lat = _parse_float(request.GET.get("user_lat"))
    user_lng = _parse_float(request.GET.get("user_lng"))
    max_distance_km = _parse_float(request.GET.get("max_distance_km"))

    dealers = []
    request.cache_hit = True

    if getattr(request, "quota_exceeded", False):
        messages.warning(request, "Daily search limit reached. Upgrade for more searches.")
        return render(
            request,
            "dealers/search.html",
            {
                "dealers": [],
                "page_obj": [],
                "quota_exceeded": True,
                "city": city,
                "radius": radius,
                "min_rating": min_rating,
                "sort": sort,
                "open_now": open_now,
                "weekends": weekends,
                "has_contacts": has_contacts,
                "total": 0,
            },
        )

    if city:
        if not is_german_city(city):
            messages.warning(request, "Please enter a city located in Germany.")
            return render(
                request,
                "dealers/search.html",
                {
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
                },
            )

        dealers = _run_search(request, city, radius)

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
            dealers = sorted(
                dealers,
                key=lambda x: x.get("rating") or 0,
                reverse=True,
            )
        elif sort == "reviews":
            dealers = sorted(
                dealers,
                key=lambda x: x.get("reviews") or 0,
                reverse=True,
            )
        elif sort == "distance" and _is_valid_lat_lng(user_lat, user_lng):
            dealers = sorted(
                dealers,
                key=lambda x: x.get("distance_km") if x.get("distance_km") is not None else float("inf"),
            )

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

    if request.cache_hit:
        messages.info(request, "Results served from cache. Daily quota was not used.")
    else:
        messages.info(request, "Fresh search executed. Daily quota used: +1.")

    return render(request, "dealers/search.html", context)