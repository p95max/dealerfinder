from dotenv import load_dotenv
load_dotenv()

import pytest


@pytest.fixture(autouse=True)
def _force_test_settings(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }