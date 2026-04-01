from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from apps.users.views import login_gate_view


admin_path = f'{getattr(settings, "DJANGO_ADMIN_URL", "admin").strip("/")}/'

urlpatterns = [
    path(admin_path, admin.site.urls),
    path("accounts/login/", login_gate_view, name="account_login"),
    path("accounts/", include("allauth.urls")),

    path("", include("apps.core.urls")),
    path("", include("apps.dealers.urls")),
    path("users/", include("apps.users.urls")),
    path("contact/", include("apps.contact.urls")),
]