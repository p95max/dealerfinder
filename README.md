# DealerFinder

## 🧱 System Overview

`DealerFinder` is a server-rendered Django application for searching car dealers in Germany.
The system is optimized for fast and predictable search with minimal external API dependency via a cache-first approach.

The primary external dependency is the Google Places API; the majority of requests are served from cache.
Cached data has a TTL and is automatically refreshed on cache miss or expiry.

- Search is restricted to German cities (validated via Geocoding API)
- Authentication via Google OAuth only
- Anti-abuse: Cloudflare Turnstile + quotas (Redis) + throttling

---

## ⚙️ Tech Stack

**Backend:** Python 3.12, Django 6.x (FBV), PostgreSQL 18, Redis 7, Celery 5
**Frontend:** Django Templates, Bootstrap 5.3, Vanilla JS
**External APIs:** Google Places API (New), Google Geocoding API, Geolocation API, Google OAuth, OpenAI API, Telegram Bot API
**Infra:** Docker Compose v2, Gunicorn (2 workers), Nginx, Redis 7

---

## 🚀 Local Development (Docker)

The project is started via Docker Compose from the `docker/` directory.

### 1. Prepare environment

```bash
cp .env.example .env
```
⚠️ Required: before running the project, you must provide valid API keys in .env:
* Google APIs (Places API, Maps JS, OAuth)
* AI provider API key (for summaries)
* Cloudflare Turnstile

> During development, OpenAI `gpt-4o-mini` was used as the AI provider for generating summaries. The system is provider-agnostic and can be switched to any compatible AI API.

> ⚠️ Without these keys, core functionality (search, AI summaries, anti-bot protection) will not work.

### 2. Run project

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up --build
```

### 3. Open in browser

`http://localhost:8000`

### Notes

- Uses development overrides (`docker-compose.dev.yml`)
- Includes: Django + PostgreSQL + Redis + Celery + Nginx
- Hot reload enabled for development

---

## 🤖 AI

AI summary is an optional data enrichment layer.
It has no effect on search, filtering, or result ranking.

- Async generation via Celery + OpenAI
- Optional, can be disabled via feature flag
- Used only for UX enrichment

Details: [docs/ai_architecture.md](docs/ai_architecture.md)

---

## 🏗️ Architecture

```
Client (Browser)
       ↓
Middleware (RequestLoggingMiddleware → ThrottleMiddleware → LoginGateMiddleware)
       ↓
Django Views (FBV)
       ↓
Service Layer
├── Search services
├── AI module
│   ├── payload/query layer
│   ├── enqueue logic
│   ├── generation service
│   ├── Redis cache
│   ├── Redis locks
│   └── quotas / rate limits
├── PostgreSQL
├── Redis
├── Google Places API
└── OpenAI API
```

---

## 📁 Project Structure

```
dealerfinder/
├── manage.py
├── .env.example
├── pyproject.toml
│
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   ├── entrypoint.sh
│   └── nginx.conf
│
├── config/
│   ├── celery.py
│   ├── urls.py
│   └── settings/
│       ├── base.py
│       ├── dev.py
│       ├── prod.py
│       └── test.py
│
├── apps/
│   ├── contact/
│   │   ├── forms.py
│   │   ├── middleware.py    # ContactThrottleMiddleware
│   │   ├── models.py        # ContactMessage
│   │   ├── services.py      # Telegram notify + email fallback
│   │   ├── urls.py
│   │   └── views.py
│   │
│   ├── core/
│   │   ├── middleware.py    # RequestLoggingMiddleware, ClientIPMiddleware
│   │   ├── urls.py
│   │   └── views.py         # home, about, health, legal pages
│   │
│   ├── dealers/
│   │   ├── admin.py
│   │   ├── models.py        # Dealer, DealerAiSummary, SearchCache, PopularSearch, UserSearchHistory
│   │   ├── tasks.py         # generate_dealer_ai_summary_task (Celery)
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── ai/
│   │   │   ├── cache.py     # Redis cache for AI summary payloads
│   │   │   ├── enqueue.py   # enqueue_ai_summaries_for_dealers()
│   │   │   ├── locks.py     # Redis dedup lock for AI generation
│   │   │   ├── queries.py   # attach_ai_summaries_to_dealers(), payload builders
│   │   │   ├── quotas.py
│   │   │   ├── system_quota.py
│   │   │   ├── rate_limits.py
│   │   │   └── service.py   # generate_ai_summary_for_dealer(), freshness/retry helpers
│   │   ├── management/
│   │   │   └── commands/
│   │   │       ├── warm_search_cache.py
│   │   │       ├── process_pending_ai_summaries.py
│   │   │       └── purge_expired_search_cache.py
│   │   └── services/
│   │       ├── dealer_service.py           # orchestration: cache → Google → normalize → store
│   │       ├── search_cache.py             # read/write SearchCache (TTL from CACHE_TTL_HOURS)
│   │       ├── distance_service.py         # haversine
│   │       ├── geocoding_service.py        # German city validation, 30-day cache
│   │       ├── google_places.py            # Text Search + Place Details API
│   │       ├── google_places_cache_service.py  # Redis cache for Place Details
│   │       ├── google_places_lock_service.py   # Redis lock for Place Details deduplication
│   │       └── search_tracking_service.py  # PopularSearch, UserSearchHistory, anon history
│   │
│   └── users/
│       ├── admin.py
│       ├── middleware.py    # ThrottleMiddleware, LoginGateMiddleware, OAuthStartProtectionMiddleware
│       ├── models.py        # User, Favorite
│       ├── urls.py
│       ├── views.py
│       └── services/
│           ├── quota_service.py     # search quota (Redis)
│           └── ai_quota_service.py  # AI quota (Redis)
│
├── common/
│   ├── exceptions.py             # AiClientError
│   ├── redis.py                  # raw redis_client
│   └── services/
│       ├── feature_flags.py      # Redis-backed feature flags
│       └── rate_limiter.py       # RedisRateLimiter (ZSET sliding window)
│
├── integrations/
│   ├── google_oauth.py
│   ├── telegram.py
│   ├── email_notifications.py
│   └── turnstile.py
│
├── utils/
│   ├── build_cities.py      # one-time: generates static/data/cities_de.json
│   ├── logging.py           # JsonFormatter
│   └── http.py              # _get_client_ip()
│
├── templates/
├── static/
│   ├── css/
│   ├── js/
│   └── data/
│       └── cities_de.json   # ~3500 German cities for autocomplete
└── tests/
```

---

## 🔁 Request Flow

Search flow: cache-first → Google Places (on miss) → filtering → optional AI enrichment.

Details: [docs/request_flow.md](docs/request_flow.md)

---

## 🧠 Core Components

### Service Layer (`apps/dealers/services/`)

| Module | Responsibility |
|--------|----------------|
| `dealer_service.py` | Orchestration: cache → Google → normalize → `sync_dealers_to_db` |
| `search_cache.py` | Read/write `SearchCache` (TTL = `CACHE_TTL_HOURS`) |
| `google_places.py` | Text Search + Place Details API, global daily cap |
| `google_places_cache_service.py` | Redis cache for Place Details (`PLACE_DETAILS_CACHE_TTL_SECONDS`) |
| `google_places_lock_service.py` | Redis lock for deduplicating concurrent Place Details requests |
| `geocoding_service.py` | German city validation, reverse geocode, 30-day cache |
| `distance_service.py` | Haversine distance to user |
| `search_tracking_service.py` | `PopularSearch`, `UserSearchHistory`, anon history |

### AI Layer (`apps/dealers/ai/`)

| Module | Responsibility |
|--------|----------------|
| `enqueue.py` | `enqueue_ai_summaries_for_dealers()` — creates/updates `DealerAiSummary`, dispatches Celery tasks |
| `service.py` | `generate_ai_summary_for_dealer()` — OpenAI call, result persistence; freshness/retry helpers |
| `queries.py` | `attach_ai_summaries_to_dealers()`, `get_dealer_ai_summary_payload()`, `generate_dealer_ai_summary_payload()` |
| `cache.py` | Redis payload cache (`ai_summary:{place_id}`, TTL `AI_SUMMARY_CACHE_TTL_SECONDS`) |
| `locks.py` | Redis NX lock for generation deduplication (`lock:ai_summary:{place_id}`) |
| `rate_limits.py` | AI rate limits (per-minute via `RedisRateLimiter`) |

### Cache Strategy

| Parameter | Value |
|-----------|-------|
| Type | read-through |
| Cache key | `dealers:{city}:{radius_int}` |
| TTL | `CACHE_TTL_HOURS` (default 72h) |
| Storage | `SearchCache` (PostgreSQL) |
| Filters | applied in-memory after cache hit/miss |
| HIT | return without Google API call |
| MISS | Google API → normalize → `SearchCache.update_or_create` |

### Data Normalization

`normalize()` in `dealer_service.py` → internal format:

```json
{
  "place_id":    "str",
  "name":        "str",
  "address":     "str",
  "lat":         "float",
  "lng":         "float",
  "rating":      "float | None",
  "reviews":     "int | None",
  "phone":       "str | None",
  "website":     "str | None",
  "open_now":    "bool",
  "has_weekend": "bool"
}
```

---

## 🗄️ Data Model

Core entities:
- Dealer
- SearchCache
- User
- Favorite

Details: [docs/data_model.md](docs/data_model.md)

---

## Filtering

> Search is restricted to German cities. Requests for other countries are rejected.

1. **radius** — radius in km (allowed: 1, 5, 10, 20, 30, 50, 100, 200, 300; default: 20)
2. **rating + reviews** — weighted score: `rating * log1p(reviews)` (confidence-adjusted)
3. **open_now** — currently open
4. **weekends** — open on weekends
5. **types** — dealer/car showroom only (via `types` field, not by name)
6. **contacts** — has phone or website

Filters and sorting are applied **in-memory** (`filter_and_sort_dealers()`) after retrieval from cache.

### Ranking

Sort modes: `score` (weighted rating × log1p reviews), `rating`, `reviews`, `distance` (if user coordinates provided). Permissive filtering: if hours/weekend data is missing — the dealer is not excluded.

---

## ⚡ Performance

- Cache-first, TTL configurable via `CACHE_TTL_HOURS` (default 72h)
- FieldMask — only required fields from Google
- Place Details — Redis cache `PLACE_DETAILS_CACHE_TTL_SECONDS` (default 24h) + Redis lock (deduplication)
- AI summary payload — Redis cache `AI_SUMMARY_CACHE_TTL_SECONDS` (default 6h), only `done`/`failed` cached
- Geocoding cached for 30 days
- Pagination: 20 results per page
- DB indexes: `city`, `lat`, `lng`, `last_synced_at`

---

## Auth

- Single auth method — **Google OAuth** (`django-allauth`)
- `LoginGateMiddleware` — blocks direct access to `/accounts/google/login/` without passing Turnstile
- On first login — mandatory AGB/Datenschutz acceptance (`terms_accepted`)
- Anonymous quota: Redis-backed by IP + day bucket
- Quota consumed in search flow/service layer
- Anonymous session: UX search history and consent state
- Account deletion — cascading delete of all user data (GDPR)
- ⚠️ Re-authentication via the same Google account after deletion creates a new User — fix before prod

---

## 💸 Cost Control

- Cache is the primary tool (`CACHE_TTL_HOURS=72`)
- FieldMask on all Google requests
- Global daily cap: `MAX_GOOGLE_CALLS_PER_DAY=500` → when reached, service operates from cache only
- Quota consumed only on cache MISS
- Place Details cached in Redis (parallel requests deduplicated via lock)
- Geocoding cached for 30 days
- AI: `MAX_AI_SUMMARIES_PER_DAY=200`, per-user/IP quotas
- Cache management via management commands: `warm_search_cache`, `purge_expired_search_cache`

---

## Rate Limiting

### Search Quota

| Type | Limit | Storage |
|------|-------|---------|
| Anonymous | `ANON_DAILY_LIMIT` (default 5) / day | Redis `quota:anon:{ip}:{date}`, TTL until midnight |
| Free | `FREE_DAILY_LIMIT` (default 15) / day | Redis `quota:user:{pk}:{date}` |
| Premium | `PREMIUM_DAILY_LIMIT` (default 50) / day | same |

### AI Quota

| Type | Limit | Storage |
|------|-------|---------|
| Anonymous | `ANON_AI_DAILY_LIMIT` (default 3) / day | Redis `quota:anon_ai:{ip}:{date}` |
| Free | `FREE_AI_DAILY_LIMIT` (default 15) / day | Redis `quota:ai:user:{pk}:{date}` |
| Premium | `PREMIUM_AI_DAILY_LIMIT` (default 50) / day | same |

**Throttling:** `SEARCH_THROTTLE_RATE=8` requests/minute per user (`user.pk`) or per IP. Sliding 60s window, Django cache (Redis).

**AI rate limit:** per-minute via `RedisRateLimiter` (`common/services/rate_limiter.py`) — ZSET sliding window.

**Global Google cap:** `MAX_GOOGLE_CALLS_PER_DAY=500`, counter in Redis, reset at midnight.

---

## 🔐 Anti-abuse

**Cloudflare Turnstile** (backend verification via siteverify):
- Login (via `LoginGateMiddleware` + `google_oauth_start` view)
- Account deletion
- Contact form

**`ContactThrottleMiddleware`** (Django cache):
- Anonymous: 3 POST / 10 min (by IP)
- Authenticated: 5 POST / 10 min (by `user.pk`)

---

## ⭐ Favorites

Authenticated users only.

- `Favorite` — snapshot of dealer data at the time of addition
- `POST /favorites/add/` — `get_or_create` by `(user, place_id)`
- `POST /favorites/remove/<place_id>/`
- `POST /favorites/clear/`
- `GET /favorites/` — list
- In search results: `is_favorite` flag in context

---

## 📬 Contact

- `GET/POST /contact/` — form (name, email, message)
- Turnstile verification on POST
- Saved to `ContactMessage`
- Telegram notification on each new message
- Email fallback if Telegram is unavailable; notification failure does not break the request
- `ContactThrottleMiddleware` — see Anti-abuse

---

## 🔎 Search Discovery

- **Popular cities:** `PopularSearch` incremented on every search. Top 10 on home and search views.
- **Search history:** authenticated users — `UserSearchHistory` (20 entries); anonymous — `session["search_history_cities"]` (8 cities, LIFO).
- `build_search_discovery_context(request)` — single context assembly point for home and search views.

---

## 📱 Frontend

Mobile-first: dealer list → main screen, map → secondary, filters → offcanvas.

City autocomplete from `static/data/cities_de.json` (~3500 entries, generated by `utils/build_cities.py`).

---

## 🔧 Deployment

```yaml
services:
  web           # Django + Gunicorn (2 workers)
  db            # PostgreSQL 18
  redis         # Redis 7
  nginx         # reverse proxy + static files
  celery_worker # Celery worker (concurrency=2)
```

- Web healthcheck via `/health/`
- DB and Redis healthchecks; variables read from `.env`

`entrypoint.sh`: wait-for-redis → migrate → collectstatic → create superuser → configure Google SocialApp → start.

---

## Observability

- Structured JSON logging (`utils/logging.py` → `JsonFormatter`)
- Request-level logs via `RequestLoggingMiddleware` (path, method, status, duration_ms, user_id, client_ip)
- Domain events: `search_started`, `dealer_search_executed`, `search_quota_denied`, `ai_summary_task_dispatched`, `health_check_completed`, etc.
- Health endpoint: `/health/` → DB + Redis checks, 200/503

---

## Cookie Consent / Privacy

- Cookie consent banner for third-party services
- Consent stored in session
- `/datenschutz/`, `/impressum/`, `/agb/` — static legal pages (TemplateView)

---

## Testing

See [testing.md](docs/testing.md)

- `pytest-django` + `pytest-mock`
- Test settings: SQLite in-memory, `locmem.LocMemCache`
- `conftest.py`: autouse fixture overrides CACHES to locmem

---

## Datenschutz / GDPR

See [legal_pages.md](docs/legal_pages.md)

---

## 📄 License


This project is licensed under the MIT License — see the [LICENSE](docs/LICENSE) file for details.

---

## Contacts

Author: Maksym Petrykin

Email: [m.petrykin@gmx.de](mailto:m.petrykin@gmx.de)

Telegram: [@max_p95](https://t.me/max_p95)