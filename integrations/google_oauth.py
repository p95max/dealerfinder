from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class GoogleOAuthAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        """Populate custom fields from Google account data on first login."""
        user = super().save_user(request, sociallogin, form)

        extra_data = sociallogin.account.extra_data
        user.google_sub = extra_data.get("sub")
        user.plan = "free"
        user.daily_quota = 30
        user.save(update_fields=["google_sub", "plan", "daily_quota"])

        return user