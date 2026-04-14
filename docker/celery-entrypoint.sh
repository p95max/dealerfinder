#!/bin/sh
set -e

echo "==> Waiting for Redis..."
python - <<EOF
import os
import time
import redis

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
client = redis.Redis.from_url(redis_url)

for attempt in range(30):
    try:
        client.ping()
        print("Redis is ready.")
        break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("Redis is not available.")
EOF

echo "==> Waiting for PostgreSQL..."
python - <<EOF
import os
import time
import psycopg

host = os.getenv("POSTGRES_HOST", "db")
port = os.getenv("POSTGRES_PORT", "5432")
dbname = os.getenv("POSTGRES_DB")
user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")

dsn = f"host={host} port={port} dbname={dbname} user={user} password={password}"

for attempt in range(30):
    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        print("PostgreSQL is ready.")
        break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("PostgreSQL is not available.")
EOF

echo "==> Starting Celery..."
exec "$@"