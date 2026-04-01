from django.views.generic import TemplateView
from django.shortcuts import render

from apps.dealers.services.search_tracking_service import build_search_discovery_context

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