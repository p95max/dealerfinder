from django.conf import settings
from django.db import models


class Dealer(models.Model):
    google_place_id = models.CharField(max_length=255, unique=True)

    name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=100)

    lat = models.FloatField()
    lng = models.FloatField()

    rating = models.FloatField(null=True)
    user_ratings_total = models.IntegerField(default=0)

    website = models.URLField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)

    last_synced_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class DealerAiSummary(models.Model):
    STATUS_PENDING = "pending"
    STATUS_DONE = "done"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_DONE, "Done"),
        (STATUS_FAILED, "Failed"),
    ]

    SENTIMENT_POSITIVE = "positive"
    SENTIMENT_MIXED = "mixed"
    SENTIMENT_NEGATIVE = "negative"

    SENTIMENT_CHOICES = [
        (SENTIMENT_POSITIVE, "Positive"),
        (SENTIMENT_MIXED, "Mixed"),
        (SENTIMENT_NEGATIVE, "Negative"),
    ]

    dealer = models.OneToOneField(
        "Dealer",
        on_delete=models.CASCADE,
        related_name="ai_summary",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    provider = models.CharField(max_length=50, blank=True)
    model = models.CharField(max_length=100, blank=True)
    prompt_version = models.CharField(max_length=20, default="v1")

    summary = models.TextField(blank=True)
    pros = models.JSONField(default=list, blank=True)
    cons = models.JSONField(default=list, blank=True)
    sentiment = models.CharField(
        max_length=20,
        choices=SENTIMENT_CHOICES,
        blank=True,
    )
    languages = models.JSONField(default=list, blank=True)
    export_friendly = models.BooleanField(null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)

    source_review_count = models.PositiveIntegerField(default=0)
    reviews_total_count_at_sync = models.PositiveIntegerField(default=0)
    source_fingerprint = models.CharField(max_length=64, blank=True)

    raw_response = models.JSONField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    retry_count = models.PositiveSmallIntegerField(default=0)
    last_retry_at = models.DateTimeField(null=True, blank=True)

    generated_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.dealer.name} [{self.status}]"


class SearchCache(models.Model):
    query_key = models.CharField(max_length=255, unique=True)
    results_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.query_key


class PopularSearch(models.Model):
    city = models.CharField(max_length=100, unique=True)
    count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-count", "city"]

    def __str__(self):
        return f"{self.city} ({self.count})"


class UserSearchHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="search_history",
    )
    city = models.CharField(max_length=100)
    searched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-searched_at"]

    def __str__(self):
        return f"{self.user.email} → {self.city}"