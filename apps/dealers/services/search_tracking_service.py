from django.db.models import F

from apps.dealers.models import PopularSearch, UserSearchHistory


SESSION_HISTORY_KEY = "search_history_cities"
SESSION_HISTORY_LIMIT = 8
POPULAR_CITIES_LIMIT = 10


def track_popular_city(city: str) -> None:
    obj, created = PopularSearch.objects.get_or_create(
        city=city,
        defaults={"count": 1},
    )
    if not created:
        PopularSearch.objects.filter(pk=obj.pk).update(count=F("count") + 1)


def track_user_search_history(user, city: str) -> None:
    UserSearchHistory.objects.create(user=user, city=city)

    ids_to_keep = list(
        user.search_history.order_by("-searched_at").values_list("id", flat=True)[:20]
    )
    user.search_history.exclude(id__in=ids_to_keep).delete()


def track_anon_search_history(request, city: str) -> None:
    history = request.session.get(SESSION_HISTORY_KEY, [])

    history = [item for item in history if item != city]
    history.insert(0, city)
    history = history[:SESSION_HISTORY_LIMIT]

    request.session[SESSION_HISTORY_KEY] = history


def get_anon_search_history(request) -> list[str]:
    return request.session.get(SESSION_HISTORY_KEY, [])



def get_popular_cities(limit: int = POPULAR_CITIES_LIMIT) -> list[str]:
    return list(
        PopularSearch.objects
        .order_by("-count", "city")
        .values_list("city", flat=True)[:limit]
    )