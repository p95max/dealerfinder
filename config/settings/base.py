import os
from pathlib import Path

from django.contrib.messages import constants as messages
from dotenv import load_dotenv

from config.env import require_env

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

# =========================
# CORE
# =========================

SECRET_KEY = require_env("SECRET_KEY")
DEBUG = os.getenv("DEBUG", "False") == "True"
ALLOWED_HOSTS = [h for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h]
if not DEBUG and not ALLOWED_HOSTS:
    raise ValueError("ALLOWED_HOSTS is not set")

DJANGO_ADMIN_URL = os.getenv("DJANGO_ADMIN_URL", "admin").strip().strip("/") or "admin"

TIME_ZONE = "Europe/Berlin"
USE_TZ = True
SITE_ID = 1


TRUST_X_FORWARDED_FOR = os.getenv("TRUST_X_FORWARDED_FOR", "False") == "True"

# =========================
# APPS
# =========================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",

    "apps.users.apps.UsersConfig",
    "apps.dealers.apps.DealersConfig",
    "apps.contact.apps.ContactConfig",
]

# =========================
# MIDDLEWARE
# =========================
MIDDLEWARE = [
    "apps.core.middleware.ClientIPMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.users.middleware.LoginGateMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.users.middleware.OAuthStartProtectionMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.contact.middleware.ContactThrottleMiddleware",
    "apps.users.middleware.ThrottleMiddleware",
    "apps.core.middleware.RequestLoggingMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# =========================
# TEMPLATES
# =========================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "config.context_processors.turnstile",
                "config.context_processors.user_quota_context",
                "config.context_processors.feature_flags",
            ],
        },
    },
]

# =========================
# DATABASE
# =========================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST", "db"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

# =========================
# CACHE / REDIS
# =========================
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_RATE_LIMIT_DB = os.getenv("REDIS_RATE_LIMIT_DB", "redis://redis:6379/2")
AI_SUMMARY_CACHE_TTL_SECONDS = int(os.getenv("AI_SUMMARY_CACHE_TTL_SECONDS", "21600"))
PLACE_DETAILS_CACHE_TTL_SECONDS = int(os.getenv("PLACE_DETAILS_CACHE_TTL_SECONDS", "86400"))
AI_DEDUP_LOCK_TTL_SECONDS = int(os.getenv("AI_DEDUP_LOCK_TTL_SECONDS", "60"))
GOOGLE_PLACE_DETAILS_LOCK_TTL_SECONDS = int(
    os.getenv("GOOGLE_PLACE_DETAILS_LOCK_TTL_SECONDS", "20")
)
GOOGLE_PLACE_DETAILS_LOCK_WAIT_ATTEMPTS = int(
    os.getenv("GOOGLE_PLACE_DETAILS_LOCK_WAIT_ATTEMPTS", "10")
)
GOOGLE_PLACE_DETAILS_LOCK_WAIT_SLEEP_SECONDS = float(
    os.getenv("GOOGLE_PLACE_DETAILS_LOCK_WAIT_SLEEP_SECONDS", "0.2")
)

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://redis:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# =========================
# STATIC
# =========================

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# =========================
# AUTH & ALLAUTH
# =========================

AUTH_USER_MODEL = "users.User"
LOGIN_REDIRECT_URL = "/users/accept-terms/"
LOGOUT_REDIRECT_URL = "/"
ACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_ADAPTER = "integrations.google_oauth.GoogleOAuthAdapter"
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}

# =========================
# THIRD-PARTY KEYS
# =========================
GOOGLE_API_KEY = require_env("GOOGLE_API_KEY")
TURNSTILE_SITE_KEY = require_env("TURNSTILE_SITE_KEY")
TURNSTILE_SECRET_KEY = require_env("TURNSTILE_SECRET_KEY")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# =========================
# MESSAGES
# =========================

MESSAGE_TAGS = {
    messages.ERROR: "danger",
}

# =========================
# LIMITS
# =========================
ANON_DAILY_LIMIT = int(os.getenv("ANON_DAILY_LIMIT", 5))
FREE_DAILY_LIMIT = int(os.getenv("FREE_DAILY_LIMIT", 30))
PREMIUM_DAILY_LIMIT = int(os.getenv("PREMIUM_DAILY_LIMIT", 200))

CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", 24))
MAX_GOOGLE_CALLS_PER_DAY = int(os.getenv("MAX_GOOGLE_CALLS_PER_DAY", 500))
SEARCH_THROTTLE_RATE = int(os.getenv("SEARCH_THROTTLE_RATE", 8))

ANON_AI_DAILY_LIMIT = int(os.getenv("ANON_AI_DAILY_LIMIT", "5"))
FREE_AI_DAILY_LIMIT = int(os.getenv("FREE_AI_DAILY_LIMIT", "10"))
PREMIUM_AI_DAILY_LIMIT = int(os.getenv("PREMIUM_AI_DAILY_LIMIT", "50"))

AI_RATE_LIMIT_PER_MINUTE = int(os.getenv("AI_RATE_LIMIT_PER_MINUTE", "5"))

# =========================
# LOGGING
# =========================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "utils.logging.JsonFormatter",
        },
        "simple": {
            "format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console_json": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
        "console_simple": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console_json"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console_json"],
            "level": "INFO",
            "propagate": False,
        },
        "apps.dealers": {
            "handlers": ["console_json"],
            "level": "INFO",
            "propagate": False,
        },
        "apps.users": {
            "handlers": ["console_json"],
            "level": "INFO",
            "propagate": False,
        },
        "apps.contact": {
            "handlers": ["console_json"],
            "level": "INFO",
            "propagate": False,
        },
        "integrations": {
            "handlers": ["console_json"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# =========================
# EMAIL FALLBACK
# =========================

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@example.com")
CONTACT_FALLBACK_EMAIL = os.getenv("CONTACT_FALLBACK_EMAIL", "")

# EMAIL_BACKEND = os.getenv(
#     "EMAIL_BACKEND",
#     "django.core.mail.backends.smtp.EmailBackend",
# )

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"   # dev mode

EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False") == "True"

# =========================
# AI
# =========================
AI_ENABLED = os.getenv("AI_ENABLED", "False") == "True"
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_REQUEST_TIMEOUT = int(os.getenv("AI_REQUEST_TIMEOUT", "15"))
MAX_AI_SUMMARIES_PER_DAY = int(os.getenv("MAX_AI_SUMMARIES_PER_DAY", "200"))
AI_PROMPT_VERSION = os.getenv("AI_PROMPT_VERSION", "v1")
AI_SYNC_ON_SEARCH = os.getenv("AI_SYNC_ON_SEARCH", "False") == "True"
AI_SUMMARY_TTL_DAYS = int(os.getenv("AI_SUMMARY_TTL_DAYS", "7"))
AI_FAILED_RETRY_HOURS = int(os.getenv("AI_FAILED_RETRY_HOURS", "12"))
AI_PENDING_STALE_MINUTES = int(os.getenv("AI_PENDING_STALE_MINUTES", "30"))
AI_SYNC_LIMIT = int(os.getenv("AI_SYNC_LIMIT", "5"))
FEATURE_AI_SUMMARY_ENABLED = os.getenv("FEATURE_AI_SUMMARY_ENABLED", "True") == "True"
FEATURE_PREMIUM_ENABLED = os.getenv("FEATURE_PREMIUM_ENABLED", "False") == "True"

# =========================
# CELERY
# =========================
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

CELERY_TASK_TIME_LIMIT = 120
CELERY_TASK_SOFT_TIME_LIMIT = 90

CELERY_BEAT_SCHEDULE = {
    "retry-dealer-ai-summaries-every-15-minutes": {
        "task": "apps.dealers.tasks.retry_dealer_ai_summaries_task",
        "schedule": 60 * 15,
        "args": (20,),
    },
}