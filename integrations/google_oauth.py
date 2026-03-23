from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings


class GoogleOAuthAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        """Populate custom fields from Google account data on first login."""
        user = super().save_user(request, sociallogin, form)

        extra_data = sociallogin.account.extra_data
        user.google_sub = extra_data.get("sub")

        if user.plan in (None, "", "anon"):
            user.plan = "free"
            user.daily_quota = settings.FREE_DAILY_QUOTA

        user.save(update_fields=["google_sub", "plan", "daily_quota"])

        return user