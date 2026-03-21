from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    google_sub = models.CharField(max_length=255, unique=True, null=True, blank=True)
    plan = models.CharField(max_length=20, default="anon")  # anon / free / premium
    daily_quota = models.IntegerField(default=10)
    used_today = models.IntegerField(default=0)
    last_quota_reset = models.DateField(null=True, blank=True)
    email = models.EmailField(unique=True)

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