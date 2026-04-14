import logging
import re

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.dealers.ai.enqueue import enqueue_ai_summaries_for_dealers
from apps.dealers.ai.queries import (
    attach_ai_summaries_to_dealers,
    generate_dealer_ai_summary_payload,
    get_dealer_ai_summary_payload,
)
from apps.dealers.services.dealer_service import filter_and_sort_dealers, search_dealers
from apps.dealers.services.geocoding_service import is_german_city, reverse_geocode_city
from apps.dealers.services.google_places import is_google_cap_reached
from apps.dealers.services.search_tracking_service import (
    build_search_discovery_context,
    track_anon_search_history,
    track_popular_city,
    track_user_search_history,
)
from apps.users.services.quota_service import (
    consume_anonymous_search,
    consume_authenticated_search,
    get_anonymous_quota_status,
    get_authenticated_quota_status,
)
from utils.http import _get_client_ip

logger = logging.getLogger(__name__)

DEALERS_PER_PAGE = 20
ALLOWED_RADIUS = {1, 5, 10, 20, 30, 50, 100, 200, 300}
DEFAULT_RADIUS = 20


def search_view(request):
    redirect_response = _restore_last_search_redirect(request)
    if redirect_response:
        return redirect_response

    params = _extract_search_params(request)
    _apply_anon_terms(request)

    city = params["city"]
    if not city and params["user_lat"] is not None and params["user_lng"] is not None:
        resolved = reverse_geocode_city(params["user_lat"], params["user_lng"])
        if resolved:
            city = _normalize_city(resolved)
            params["city"] = city

    dealers = []
    page_obj = []

    def build_context(**extra):
        context = {
            "dealers": [],
            "page_obj": [],
            "city": params["city"],
            "radius": params["radius"],
            "min_rating": params["min_rating"],
            "sort": params["sort"],
            "open_now": params["open_now"],
            "weekends": params["weekends"],
            "has_contacts": params["has_contacts"],
            "total": 0,
            **extra,
        }
        context.update(build_search_discovery_context(request))
        return context

    if city:
        _log_search_started(request, city, params["radius"])

        quota_status = _get_search_quota_status(request)
        quota_denied_response = _handle_quota_denied(
            request=request,
            quota_status=quota_status,
            city=city,
            radius=params["radius"],
            build_context=build_context,
        )
        if quota_denied_response:
            return quota_denied_response

        city_validation_response = _validate_search_city(
            request=request,
            city=city,
            radius=params["radius"],
            build_context=build_context,
        )
        if city_validation_response:
            return city_validation_response

        raw_dealers, from_cache = search_dealers(city=city, radius=params["radius"])
        _log_search_executed(
            request=request,
            city=city,
            radius=params["radius"],
            from_cache=from_cache,
            result_count=len(raw_dealers),
        )

        _consume_search_quota_if_needed(
            request=request,
            from_cache=from_cache,
        )

        _track_search_if_needed(request=request, city=city)

        dealers = filter_and_sort_dealers(
            raw_dealers,
            min_rating=_parse_min_rating(params["min_rating"]),
            open_now=bool(params["open_now"]),
            weekends=bool(params["weekends"]),
            has_contacts=bool(params["has_contacts"]),
            user_lat=params["user_lat"],
            user_lng=params["user_lng"],
            max_distance_km=params["max_distance_km"],
            sort=params["sort"],
        )

        _enqueue_ai_summaries_if_needed(request=request, dealers=dealers)
        _attach_favorite_flags(request=request, dealers=dealers)

        page_obj = _paginate_and_attach_ai(
            dealers=dealers,
            page_number=params["page_number"],
        )

        _apply_empty_search_message(request=request, dealers=dealers)

    return render(
        request,
        "dealers/search.html",
        build_context(
            dealers=page_obj,
            page_obj=page_obj,
            total=len(dealers),
        ),
    )


@require_POST
def dealer_ai_summary_generate_view(request, place_id):
    payload, status_code = generate_dealer_ai_summary_payload(
        place_id,
        request=request,
    )
    return JsonResponse(payload, status=status_code)


def dealer_ai_summary_view(request, place_id):
    payload, status_code = get_dealer_ai_summary_payload(
        place_id,
        request=request,
    )
    return JsonResponse(payload, status=status_code)


# =========================
# SEARCH FLOW HELPERS
# =========================
def _restore_last_search_redirect(request):
    if request.method == "GET" and request.GET.get("city"):
        params = request.GET.copy()
        params.pop("page", None)
        request.session["last_search_params"] = params.urlencode()
        return None

    if request.method == "GET" and not request.GET and request.session.get("last_search_params"):
        return redirect(f"{request.path}?{request.session['last_search_params']}")

    return None


def _extract_search_params(request) -> dict:
    return {
        "city": _normalize_city(request.GET.get("city") or ""),
        "radius": _parse_radius(request.GET.get("radius")),
        "min_rating": request.GET.get("min_rating"),
        "sort": request.GET.get("sort", "score"),
        "open_now": request.GET.get("open_now"),
        "weekends": request.GET.get("weekends"),
        "has_contacts": request.GET.get("has_contacts"),
        "page_number": request.GET.get("page", 1),
        "user_lat": _parse_float(request.GET.get("user_lat")),
        "user_lng": _parse_float(request.GET.get("user_lng")),
        "max_distance_km": _parse_float(request.GET.get("max_distance_km")),
    }


def _apply_anon_terms(request) -> None:
    if request.GET.get("accept_terms") and not request.user.is_authenticated:
        request.session["anon_terms"] = True


def _get_search_quota_status(request):
    if request.user.is_authenticated:
        return get_authenticated_quota_status(request.user)
    return get_anonymous_quota_status(request)


def _handle_quota_denied(request, quota_status, city, radius, build_context):
    if quota_status.allowed:
        return None

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
            "Daily search limit reached. "
            "Upgrade to Premium for "
            f"{getattr(__import__('django.conf').conf.settings, 'PREMIUM_DAILY_LIMIT', '')} searches/day.",
        )
    else:
        messages.warning(
            request,
            f"Daily limit reached. Create a free account for "
            f"{getattr(__import__('django.conf').conf.settings, 'FREE_DAILY_LIMIT', '')} searches/day.",
        )

    return render(request, "dealers/search.html", build_context(quota_exceeded=True))


def _validate_search_city(request, city, radius, build_context):
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

    return None


def _log_search_started(request, city, radius) -> None:
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


def _log_search_executed(request, city, radius, from_cache, result_count) -> None:
    logger.info(
        "Dealer search executed",
        extra={
            "event": "dealer_search_executed",
            "user_id": _get_user_id(request),
            "is_authenticated": request.user.is_authenticated,
            "city": city,
            "radius": radius,
            "from_cache": from_cache,
            "result_count": result_count,
        },
    )


def _consume_search_quota_if_needed(request, from_cache: bool) -> None:
    if from_cache:
        return

    if request.user.is_authenticated:
        consume_authenticated_search(request.user)
    else:
        consume_anonymous_search(request)


def _track_search_if_needed(request, city: str) -> None:
    if not _should_track_search(request):
        return

    if request.user.is_authenticated:
        track_user_search_history(request.user, city)
    else:
        track_anon_search_history(request, city)

    track_popular_city(city)


def _enqueue_ai_summaries_if_needed(request, dealers: list[dict]) -> None:
    if not dealers:
        return

    top_place_ids = [
        dealer.get("place_id")
        for dealer in dealers[:settings.AI_SYNC_LIMIT]
        if dealer.get("place_id")
    ]

    enqueue_ai_summaries_for_dealers(
        top_place_ids,
        limit=settings.AI_SYNC_LIMIT,
        user_id=request.user.id if request.user.is_authenticated else None,
        client_ip=_get_client_ip(request),
    )


def _attach_favorite_flags(request, dealers: list[dict]) -> None:
    if request.user.is_authenticated and dealers:
        favorite_place_ids = set(
            request.user.favorites.values_list("place_id", flat=True)
        )
        for dealer in dealers:
            dealer["is_favorite"] = dealer.get("place_id") in favorite_place_ids
        return

    for dealer in dealers:
        dealer["is_favorite"] = False


def _paginate_and_attach_ai(dealers: list[dict], page_number):
    paginator = Paginator(dealers, DEALERS_PER_PAGE)
    page_obj = paginator.get_page(page_number)

    current_page_dealers = list(page_obj.object_list)
    if current_page_dealers:
        attach_ai_summaries_to_dealers(current_page_dealers)

    return page_obj


def _apply_empty_search_message(request, dealers: list[dict]) -> None:
    if not dealers and is_google_cap_reached():
        messages.warning(
            request,
            "Live search is temporarily unavailable. Try a city that was searched before.",
        )
    elif not dealers:
        messages.warning(request, "No dealers found. Please enter a city in Germany.")


# =========================
# HELPERS
# =========================
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