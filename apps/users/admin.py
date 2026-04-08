from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "plan",
        "daily_quota",
        "used_today",
        "ai_daily_quota",
        "ai_used_today",
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
                    "used_today",
                    "last_quota_reset",
                )
            },
        ),
        (
            "AI Quota",
            {
                "fields": (
                    "ai_daily_quota",
                    "ai_used_today",
                    "last_ai_quota_reset",
                )
            },
        ),
        ("Google", {"fields": ("google_sub",)}),
    )