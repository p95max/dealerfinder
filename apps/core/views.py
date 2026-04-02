from django.views.generic import TemplateView
from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache

from apps.dealers.services.search_tracking_service import build_search_discovery_context

def health_view(request):
    status = "ok"
    checks = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "error"
        status = "degraded"

    try:
        cache.set("health_check", "ok", timeout=5)
        if cache.get("health_check") == "ok":
            checks["redis"] = "ok"
        else:
            raise Exception("cache mismatch")
    except Exception:
        checks["redis"] = "error"
        status = "degraded"

    http_status = 200 if status == "ok" else 503

    return JsonResponse(
        {
            "status": status,
            "checks": checks,
        },
        status=http_status,
    )


def home_view(request):
    context = build_search_discovery_context(request)
    return render(request, "home.html", context)


def about_view(request):
    return render(request, "about.html")



class ImpressumView(TemplateView):
    template_name = "legal/impressum.html"



class DatenschutzView(TemplateView):
    template_name = "legal/datenschutz.html"



class AGBView(TemplateView):
    template_name = "legal/agb.html"