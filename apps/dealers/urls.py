from django.urls import path

from .views import search_view

app_name = 'dealers'

urlpatterns = [
    path('', search_view, name='home'),
    path('search/', search_view, name='search'),
]