from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("profile/", views.profile_view, name="profile"),
    path("quota-status/", views.quota_status, name="quota_status"),
    path("delete/", views.delete_account_view, name="delete_account"),
]