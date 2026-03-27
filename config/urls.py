from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView


admin_path = f'{getattr(settings, "ADMIN_URL", "admin").strip("/")}/'

urlpatterns = [
    path(admin_path, admin.site.urls),
    path(
        "accounts/login/",
        RedirectView.as_view(pattern_name="google_login"),
        name="account_login",
    ),
    path("accounts/", include("allauth.urls")),
    path("", include("apps.dealers.urls")),
    path("users/", include("apps.users.urls")),
]