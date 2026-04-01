from django.urls import path

from . import views
from .views import ImpressumView, DatenschutzView, AGBView

urlpatterns = [
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),

    path("impressum/", ImpressumView.as_view(), name="impressum"),
    path("datenschutz/", DatenschutzView.as_view(), name="datenschutz"),
    path("agb/", AGBView.as_view(), name="agb"),
]