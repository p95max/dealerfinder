from django.urls import path
from django.views.generic import TemplateView

from . import views


app_name = 'dealers'

urlpatterns = [
    path('search/', views.search_view, name='search'),
]