from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "plan",
        "daily_quota",
        "ai_daily_quota",
        "is_active",
        "date_joined",
    )
    list_filter = ("plan", "is_active", "is_staff")
    search_fields = ("email", "google_sub")
    ordering = ("-date_joined",)

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Search Quota",
            {
                "fields": (
                    "plan",
                    "daily_quota",
                )
            },
        ),
        (
            "AI Quota",
            {
                "fields": (
                    "ai_daily_quota",
                )
            },
        ),
        ("Google", {"fields": ("google_sub",)}),
    )