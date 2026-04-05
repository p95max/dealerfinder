from django.urls import path
from django.views.generic import TemplateView

from . import views


app_name = 'dealers'

urlpatterns = [
    path('search/', views.search_view, name='search'),
    path('dealer/<str:place_id>/ai-summary/', views.dealer_ai_summary_view, name='dealer_ai_summary'),
]