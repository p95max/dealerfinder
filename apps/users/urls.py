from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("delete/", views.delete_account_view, name="delete_account"),
]