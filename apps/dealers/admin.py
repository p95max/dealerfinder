from django.contrib import admin

from .models import Dealer, SearchCache, PopularSearch, UserSearchHistory

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


@admin.register(PopularSearch)
class PopularSearchAdmin(admin.ModelAdmin):
    list_display = ("city", "count", "updated_at")
    ordering = ("-count", "city")
    search_fields = ("city",)


@admin.register(UserSearchHistory)
class UserSearchHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "city", "searched_at")
    ordering = ("-searched_at",)
    search_fields = ("user__email", "city")


