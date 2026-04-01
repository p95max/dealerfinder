from django.views.generic import TemplateView
from django.shortcuts import render

def home_view(request):
    return render(request, "home.html")


def about_view(request):
    return render(request, "about.html")

class ImpressumView(TemplateView):
    template_name = "legal/impressum.html"


class DatenschutzView(TemplateView):
    template_name = "legal/datenschutz.html"


class AGBView(TemplateView):
    template_name = "legal/agb.html"