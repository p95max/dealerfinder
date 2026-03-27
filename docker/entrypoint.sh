#!/bin/sh
set -e

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Creating cache table..."
python manage.py createcachetable

echo "==> Creating superuser..."
python manage.py shell -c "
from apps.users.models import User
email = '$DJANGO_SUPERUSER_EMAIL'
password = '$DJANGO_SUPERUSER_PASSWORD'
if not email or not password:
    print('DJANGO_SUPERUSER_EMAIL or DJANGO_SUPERUSER_PASSWORD not set, skipping.')
elif User.objects.filter(email=email).exists():
    print(f'Superuser already exists, skipping.')
else:
    User.objects.create_superuser(username='admin', email=email, password=password)
    print(f'Superuser created.')
"

echo "==> Setting up Google SocialApp..."
python manage.py shell -c "
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
import os

domain = os.getenv('SITE_DOMAIN', 'localhost:8000')
client_id = os.getenv('GOOGLE_CLIENT_ID', '')
client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '')

if not client_id or not client_secret:
    print('GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set, skipping.')
else:
    site, _ = Site.objects.update_or_create(
        id=1,
        defaults={'domain': domain, 'name': 'DealerFinder'},
    )
    app, created = SocialApp.objects.get_or_create(
        provider='google',
        defaults={'name': 'Google', 'client_id': client_id, 'secret': client_secret},
    )
    if not created:
        app.client_id = client_id
        app.secret = client_secret
        app.save(update_fields=['client_id', 'secret'])
    app.sites.add(site)
    print(f'Google SocialApp configured for {domain}.')
"

echo "==> Starting server..."
exec "$@"