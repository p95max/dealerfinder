from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = 'dealers'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('search/', views.search_view, name='search'),
    path("agb/", TemplateView.as_view(template_name="legal/agb.html"), name="agb"),
    path("datenschutz/", TemplateView.as_view(template_name="legal/datenschutz.html"), name="datenschutz"),

]