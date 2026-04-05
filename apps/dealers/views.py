import re
import time
import logging

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect

from apps.dealers.models import DealerAiSummary, Dealer
from apps.dealers.services.dealer_ai_service import generate_ai_summary_for_dealer
from apps.dealers.services.dealer_service import search_dealers, filter_and_sort_dealers
from apps.dealers.services.geocoding_service import is_german_city
from apps.dealers.services.google_places import is_google_cap_reached
from apps.dealers.services.search_tracking_service import (
    track_anon_search_history,
    track_popular_city,
    track_user_search_history,
    build_search_discovery_context,
)
from apps.users.services.quota_service import (
    get_authenticated_quota_status,
    get_anonymous_quota_status,
    consume_authenticated_search,
    consume_anonymous_search,
)
from utils.http import _get_client_ip
from django.http import JsonResponse
from apps.dealers.models import Dealer, DealerAiSummary
from apps.dealers.services.dealer_ai_service import generate_ai_summary_for_dealer

logger = logging.getLogger(__name__)

DEALERS_PER_PAGE = 20
ALLOWED_RADIUS = {1, 5, 10, 20, 30, 50, 100, 200, 300}
DEFAULT_RADIUS = 20
AI_SYNC_LIMIT = 5


def _should_track_search(request) -> bool:
    return bool(request.GET.get("city")) and not request.GET.get("page")


def _parse_float(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


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


def _parse_min_rating(value) -> float | None:
    try:
        return float(value) if value else None
    except (TypeError, ValueError):
        return None


def _get_user_id(request):
    return request.user.pk if request.user.is_authenticated else None


def _sync_ai_summaries(place_ids: list[str]) -> None:
    """Fire-and-forget AI summary generation for a batch of place IDs."""
    dealers_qs = Dealer.objects.filter(google_place_id__in=place_ids[:AI_SYNC_LIMIT])
    for dealer_obj in dealers_qs:
        try:
            generate_ai_summary_for_dealer(dealer_obj)
        except Exception:
            logger.exception(
                "Inline AI summary generation failed",
                extra={"event": "ai_sync_on_search_failed", "place_id": dealer_obj.google_place_id},
            )


def dealer_ai_summary_view(request, place_id):
    try:
        dealer = Dealer.objects.get(google_place_id=place_id)
    except Dealer.DoesNotExist:
        return JsonResponse({"status": "failed"}, status=404)

    ai = generate_ai_summary_for_dealer(dealer)

    return JsonResponse({
        "status": ai.status,
        "summary": ai.summary or "",
        "pros": ai.pros or [],
        "cons": ai.cons or [],
    })


def search_view(request):
    started_at = time.monotonic()

    if request.method == "GET" and request.GET.get("city"):
        params = request.GET.copy()
        params.pop("page", None)
        request.session["last_search_params"] = params.urlencode()
    elif request.method == "GET" and not request.GET and request.session.get("last_search_params"):
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

    def build_context(**extra):
        context = {
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
        context.update(build_search_discovery_context(request))
        return context

    if city:
        logger.info(
            "Search request started",
            extra={
                "event": "search_started",
                "user_id": _get_user_id(request),
                "is_authenticated": request.user.is_authenticated,
                "client_ip": _get_client_ip(request),
                "path": request.path,
                "method": request.method,
                "city": city,
                "radius": radius,
            },
        )

        if request.user.is_authenticated:
            quota_status = get_authenticated_quota_status(request.user)
        else:
            quota_status = get_anonymous_quota_status(request)

        if not quota_status.allowed:
            logger.warning(
                "Search denied by quota",
                extra={
                    "event": "search_quota_denied",
                    "user_id": _get_user_id(request),
                    "is_authenticated": request.user.is_authenticated,
                    "city": city,
                    "radius": radius,
                    "quota_allowed": False,
                    "status_code": 200,
                },
            )
            if request.user.is_authenticated:
                messages.warning(
                    request,
                    f"Daily search limit reached. Upgrade to Premium for {settings.PREMIUM_DAILY_LIMIT} searches/day.",
                )
            else:
                messages.warning(
                    request,
                    f"Daily limit reached. Create a free account for {settings.FREE_DAILY_LIMIT} searches/day.",
                )
            return render(request, "dealers/search.html", build_context(quota_exceeded=True))

        if not _is_valid_city(city):
            logger.warning(
                "Search rejected: invalid city",
                extra={
                    "event": "search_invalid_city",
                    "user_id": _get_user_id(request),
                    "is_authenticated": request.user.is_authenticated,
                    "city": city,
                    "radius": radius,
                    "status_code": 200,
                },
            )
            messages.warning(request, "Please enter a valid city name.")
            return render(request, "dealers/search.html", build_context())

        if not is_german_city(city):
            logger.warning(
                "Search rejected: city outside Germany",
                extra={
                    "event": "search_city_outside_germany",
                    "user_id": _get_user_id(request),
                    "is_authenticated": request.user.is_authenticated,
                    "city": city,
                    "radius": radius,
                    "status_code": 200,
                },
            )
            messages.warning(request, "Please enter a city located in Germany.")
            return render(request, "dealers/search.html", build_context())

        raw_dealers, from_cache = search_dealers(city=city, radius=radius)

        logger.info(
            "Dealer search executed",
            extra={
                "event": "dealer_search_executed",
                "user_id": _get_user_id(request),
                "is_authenticated": request.user.is_authenticated,
                "city": city,
                "radius": radius,
                "from_cache": from_cache,
                "result_count": len(raw_dealers),
            },
        )

        if not from_cache:
            if request.user.is_authenticated:
                consume_authenticated_search(request.user)
            else:
                consume_anonymous_search(request)

        if _should_track_search(request):
            if request.user.is_authenticated:
                track_user_search_history(request.user, city)
            else:
                track_anon_search_history(request, city)
            track_popular_city(city)

        dealers = filter_and_sort_dealers(
            raw_dealers,
            min_rating=_parse_min_rating(min_rating),
            open_now=bool(open_now),
            weekends=bool(weekends),
            has_contacts=bool(has_contacts),
            user_lat=user_lat,
            user_lng=user_lng,
            max_distance_km=max_distance_km,
            sort=sort,
        )

        place_ids = [dealer.get("place_id") for dealer in dealers if dealer.get("place_id")]

        if not from_cache and settings.AI_ENABLED and settings.AI_SYNC_ON_SEARCH:
            _sync_ai_summaries(place_ids)

        ai_summary_map = {
            item.dealer.google_place_id: item
            for item in DealerAiSummary.objects.select_related("dealer").filter(
                dealer__google_place_id__in=place_ids
            )
        }

        for dealer in dealers:
            ai = ai_summary_map.get(dealer.get("place_id"))
            if ai:
                dealer["ai_summary"] = {
                    "status": ai.status,
                    "summary": ai.summary or "",
                    "pros": ai.pros or [],
                    "cons": ai.cons or [],
                }
            else:
                dealer["ai_summary"] = {
                    "status": "pending",
                    "summary": "",
                    "pros": [],
                    "cons": [],
                }

        logger.info(
            "AI summaries attached to search results",
            extra={
                "event": "ai_summaries_attached",
                "place_ids_count": len(place_ids),
                "ai_summary_map_count": len(ai_summary_map),
                "place_ids": place_ids[:5],
            },
        )

        if not dealers and is_google_cap_reached():
            messages.warning(
                request,
                "Live search is temporarily unavailable. Try a city that was searched before.",
            )
        elif not dealers:
            messages.warning(request, "No dealers found. Please enter a city in Germany.")

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

    return render(
        request,
        "dealers/search.html",
        build_context(
            dealers=page_obj,
            page_obj=page_obj,
            total=len(dealers),
        ),
    )

