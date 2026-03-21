from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path("accounts/login/", RedirectView.as_view(pattern_name="google_login"), name="account_login"),
    path("accounts/", include("allauth.urls")),

    path('', include('apps.dealers.urls')),

]