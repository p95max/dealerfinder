from django.contrib import admin

from .models import Dealer, SearchCache, ContactMessage


@admin.register(Dealer)
class DealerAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "rating", "user_ratings_total", "last_synced_at")
    list_filter = ("city",)
    search_fields = ("name", "address", "google_place_id")
    ordering = ("-last_synced_at",)
    readonly_fields = ("last_synced_at",)


@admin.register(SearchCache)
class SearchCacheAdmin(admin.ModelAdmin):
    list_display = ("query_key", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at", "is_read")
    list_filter = ("is_read",)
    ordering = ("-created_at",)