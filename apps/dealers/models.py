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


class SearchCache(models.Model):
    query_key = models.CharField(max_length=255, unique=True)
    results_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.query_key