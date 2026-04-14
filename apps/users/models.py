from django.contrib.auth.models import AbstractUser
from django.db import models

from django.conf import settings


class User(AbstractUser):
    google_sub = models.CharField(max_length=255, unique=True, null=True, blank=True)
    plan = models.CharField(max_length=20, default="free")
    daily_quota = models.IntegerField(default=settings.FREE_DAILY_LIMIT)
    email = models.EmailField(unique=True)
    terms_accepted = models.BooleanField(default=False)
    ai_daily_quota = models.IntegerField(default=settings.FREE_AI_DAILY_LIMIT)

    groups = models.ManyToManyField(
        "auth.Group",
        related_name="users_user_set",
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="users_user_set",
        blank=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        indexes = [
            models.Index(fields=["google_sub"]),
        ]

    def __str__(self):
        return self.email



class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    place_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    rating = models.FloatField(null=True, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(max_length=500, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "place_id")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} → {self.name}"