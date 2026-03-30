from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("profile/", views.profile_view, name="profile"),
    path("delete/", views.delete_account_view, name="delete_account"),
    path("favorites/", views.favorites_view, name="favorites"),
    path("favorites/add/", views.favorite_add_view, name="favorite_add"),
    path("favorites/remove/<str:place_id>/", views.favorite_remove_view, name="favorite_remove"),
    path("favorites/clear/", views.favorites_clear_view, name="favorites_clear"),
    path("accept-terms/", views.accept_terms_view, name="accept_terms"),
    path("anon-accept-terms/", views.anon_accept_terms_view, name="anon_accept_terms"),
    path("cookie-consent/", views.cookie_consent_view, name="cookie_consent"),
    path("quota-status/", views.quota_status, name="quota_status"),
    path("pricing/", views.pricing_view, name="pricing"),
]