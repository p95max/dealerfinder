# DealerFinder

## 🧱 System Overview

`DealerFinder` — server-rendered Django-приложение для поиска автодилеров в Германии. Веб-система для поиска, фильтрации и структурированного подбора сервисных организаций с использованием внешнего геоданных-провайдера и механизмов ограничения API-потребления.

- Cache-first интеграция с Google Places API
- Поиск только по городам Германии (валидация через Geocoding API)
- Авторизация только через Google OAuth
- Anti-abuse: Cloudflare Turnstile + квоты (Redis) + троттлинг
- AI-обогащение дилеров через Celery + OpenAI

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

## 📁 Структура проекта

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
│   │       ├── dealer_service.py           # оркестрация: cache → Google → normalize → store
│   │       ├── search_cache.py             # read/write SearchCache (TTL из CACHE_TTL_HOURS)
│   │       ├── distance_service.py         # haversine
│   │       ├── geocoding_service.py        # валидация города DE, кэш 30 дней
│   │       ├── google_places.py            # Text Search + Place Details API
│   │       ├── google_places_cache_service.py  # Redis кэш для Place Details
│   │       ├── google_places_lock_service.py   # Redis lock для дедупликации Place Details
│   │       └── search_tracking_service.py  # PopularSearch, UserSearchHistory, анон-история
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
│   ├── build_cities.py      # one-time: генерирует static/data/cities_de.json
│   ├── logging.py           # JsonFormatter
│   └── http.py              # _get_client_ip()
│
├── templates/
├── static/
│   ├── css/
│   ├── js/
│   └── data/
│       └── cities_de.json   # ~3500 немецких городов для autocomplete
└── tests/
```

---

## 🔁 Request Flow

### 🔍 Search

```
GET /search/?city=Berlin&radius=10
       ↓
ThrottleMiddleware — rate limit по user.pk / IP (Django cache, 60s time window)
       ↓
search_view
       ↓
quota_service — get_authenticated_quota_status() / get_anonymous_quota_status()
    → denied → 200 + warning message
       ↓
is_german_city() — Geocoding API (кэш 30 дней)
       ↓
search_dealers()
    → cache HIT  → return (data, from_cache=True)
    → cache MISS → Google Places API → normalize → sync_dealers_to_db() → set_cache() → return (data, False)
       ↓
Quota consume — только если cache MISS
       ↓
filter_and_sort_dealers() — in-memory фильтрация и сортировка
       ↓
enqueue_ai_summaries_for_dealers() — top-N дилеров в Celery (если AI_ENABLED)
       ↓
attach_ai_summaries_to_dealers() — прикрепить готовые AI-саммари к текущей странице
       ↓
Paginator (20/страница) → Template render
```

### 📍 Place Details

```
GET /dealer/{place_id}/ai-summary/       → get_dealer_ai_summary_payload() → JsonResponse
POST /dealer/{place_id}/ai-summary/generate/ → generate_dealer_ai_summary_payload() → JsonResponse
```

### 🤖 AI Summary (Celery)

```
generate_dealer_ai_summary_task.delay(place_id)
       ↓
acquire_ai_summary_lock()
       ↓
get_place_details()  # Redis cache + lock around Place Details
       ↓
build AI context + validate review availability
       ↓
freshness / retry / fingerprint checks
       ↓
check AI quota (per-user/IP + system cap)
       ↓
OpenAI API
       ↓
DealerAiSummary.save(status=done/failed)
       ↓
invalidate cached payload
       ↓
release_ai_summary_lock()
```

---

## 🧠 Core Components

### Service Layer (`apps/dealers/services/`)

| Модуль | Ответственность |
|--------|----------------|
| `dealer_service.py` | оркестрация: cache → Google → normalize → `sync_dealers_to_db` |
| `search_cache.py` | read/write `SearchCache` (TTL = `CACHE_TTL_HOURS`) |
| `google_places.py` | Text Search + Place Details API, global daily cap |
| `google_places_cache_service.py` | Redis кэш для Place Details (`PLACE_DETAILS_CACHE_TTL_SECONDS`) |
| `google_places_lock_service.py` | Redis lock для дедупликации параллельных Place Details запросов |
| `geocoding_service.py` | валидация города DE, reverse geocode, кэш 30 дней |
| `distance_service.py` | haversine расстояние до пользователя |
| `search_tracking_service.py` | `PopularSearch`, `UserSearchHistory`, анон-история |

### AI Layer (`apps/dealers/ai/`)

| Модуль | Ответственность |
|--------|----------------|
| `enqueue.py` | `enqueue_ai_summaries_for_dealers()` — создаёт/обновляет `DealerAiSummary`, диспатчит Celery-задачи |
| `service.py` | `generate_ai_summary_for_dealer()` — OpenAI вызов, запись результата; freshness/retry helpers |
| `queries.py` | `attach_ai_summaries_to_dealers()`, `get_dealer_ai_summary_payload()`, `generate_dealer_ai_summary_payload()` |
| `cache.py` | Redis кэш payload (`ai_summary:{place_id}`, TTL `AI_SUMMARY_CACHE_TTL_SECONDS`) |
| `locks.py` | Redis NX lock для дедупликации генерации (`lock:ai_summary:{place_id}`) |
| `rate_limits.py` | AI rate limits (per-minute через `RedisRateLimiter`) |

### Cache Strategy

| Параметр | Значение |
|----------|----------|
| Тип | read-through |
| Cache key | `dealers:{city}:{radius_int}` |
| TTL | `CACHE_TTL_HOURS` (default 72ч) |
| Storage | `SearchCache` (PostgreSQL) |
| Фильтры | применяются in-memory после cache hit/miss |
| HIT | возврат без Google API |
| MISS | Google API → normalize → `SearchCache.update_or_create` |

### Data Normalization

`normalize()` в `dealer_service.py` → внутренний формат:

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

## 🗄️ Data Storage

### `Dealer`

| Поле | Тип |
|------|-----|
| `google_place_id` | str (unique) |
| `name`, `address`, `city` | str |
| `lat`, `lng` | float |
| `rating` | float \| null |
| `user_ratings_total` | int |
| `website`, `phone` | str \| null |
| `last_synced_at` | datetime (auto_now) |

### `DealerAiSummary`

OneToOne к `Dealer` (related_name `ai_summary`). Создаётся автоматически при `sync_dealers_to_db`.

| Поле | Тип |
|------|-----|
| `status` | `pending` / `done` / `failed` |
| `provider`, `model`, `prompt_version` | str |
| `summary` | text |
| `pros`, `cons` | JSON array |
| `sentiment` | `positive` / `mixed` / `negative` \| blank |
| `languages` | JSON array |
| `export_friendly` | bool \| null |
| `confidence` | float \| null |
| `source_review_count` | int |
| `source_fingerprint` | str (SHA-64, идемпотентность) |
| `raw_response` | JSON \| null |
| `last_error` | text |
| `generated_at`, `updated_at` | datetime |

Freshness: `AI_SUMMARY_TTL_DAYS`. Retry failed: `AI_FAILED_RETRY_HOURS`. Stale pending: `AI_PENDING_STALE_MINUTES`.

### `SearchCache`

| Поле | Тип |
|------|-----|
| `query_key` | str (unique) |
| `results_json` | json |
| `created_at` | datetime |

### `User`

| Поле | Тип |
|------|-----|
| `email` | str (unique, USERNAME_FIELD) |
| `google_sub` | str \| null (unique) |
| `plan` | str (`free` / `premium`) |
| `daily_quota` | int (default 15) |
| `ai_daily_quota` | int (default 15) |
| `terms_accepted` | bool |

> ℹ️ Счётчики использования (`used_today`) вынесены в Redis: `quota:user:{pk}:{date}` и `quota:anon:{ip}:{date}`, TTL до следующей полуночи.

### `Favorite`

| Поле | Тип |
|------|-----|
| `user` | FK→User |
| `place_id` | str |
| `name`, `address`, `city` | str |
| `rating` | float \| null |
| `phone`, `website` | str |
| `lat`, `lng` | float \| null |
| `created_at` | datetime |

unique_together: `(user, place_id)`

### `PopularSearch`

| Поле | Тип |
|------|-----|
| `city` | str (unique) |
| `count` | int |
| `updated_at` | datetime (auto_now) |

### `UserSearchHistory`

| Поле | Тип |
|------|-----|
| `user` | FK→User |
| `city` | str |
| `searched_at` | datetime |

---

## Фильтрация

> Поиск ограничен городами Германии. Запросы для других стран отклоняются.

1. **radius** — радиус в км (allowed: 1, 5, 10, 20, 30, 50, 100, 200, 300; default: 20)
2. **rating + reviews** — weighted score: `rating * log1p(reviews)` (confidence-adjusted)
3. **open_now** — открыто сейчас
4. **weekends** — работает в выходные
5. **types** — только Händler/Autohaus (через `types`, не по названию)
6. **contacts** — есть телефон или сайт

Фильтры и сортировка применяются **in-memory** (`filter_and_sort_dealers()`) после получения из кэша.

### Ранжирование

Sort modes: `score` (weighted rating × log1p reviews), `rating`, `reviews`, `distance` (если переданы координаты пользователя). Permissive filtering: если часы/выходные не заполнены — не исключается.

---

## ⚙️ Tech Stack

**Backend:** Python 3.12, Django 6.x (FBV), PostgreSQL 18, Redis 7, Celery 5

**Frontend:** Django Templates, Bootstrap 5.3, Vanilla JS

**External APIs:** Google Places API (New), Google Geocoding API, Geolocation API, Google OAuth, OpenAI API, Telegram Bot API

**Infra:** Docker Compose v2, Gunicorn (2 workers), Nginx, Redis 7

---

## ⚡ Performance

- Cache-first, TTL настраивается через `CACHE_TTL_HOURS` (default 72ч)
- FieldMask — только нужные поля от Google
- Place Details — Redis кэш `PLACE_DETAILS_CACHE_TTL_SECONDS` (default 24ч) + Redis lock (дедупликация)
- AI summary payload — Redis кэш `AI_SUMMARY_CACHE_TTL_SECONDS` (default 6ч), кэшируются только `done`/`failed`
- Геокодирование кэшируется 30 дней
- Пагинация: 20 результатов на страницу
- DB индексы: `city`, `lat`, `lng`, `last_synced_at`

---

## Auth

- Единственный способ — **Google OAuth** (`django-allauth`)
- `LoginGateMiddleware` — блокирует прямой переход на `/accounts/google/login/` без прохождения Turnstile
- При первом входе — обязательное принятие AGB/Datenschutz (`terms_accepted`)
- Анонимная quota: Redis-backed по IP + day bucket
- Квота списывается в search flow/service layer
- Session для анонима: UX-история поиска и consent-state
- Удаление аккаунта — каскадное удаление всех данных (DSGVO)
- ⚠️ Повторная авторизация через тот же Google-аккаунт после удаления создаёт нового User — исправить перед prod

---

## 💸 Cost Control

- Кэш — основной инструмент (`CACHE_TTL_HOURS=72`)
- FieldMask на всех запросах к Google
- Глобальный daily cap: `MAX_GOOGLE_CALLS_PER_DAY=500` → при достижении сервис работает только из кэша
- Квота списывается только за cache MISS
- Place Details кэшируются в Redis (не запрашиваются повторно при параллельных запросах — lock)
- Геокодирование кэшируется 30 дней
- AI: `MAX_AI_SUMMARIES_PER_DAY=200`, per-user/IP квоты
- Управление кэшем через management commands: `warm_search_cache`, `purge_expired_search_cache`

---

## Rate Limiting

### Search Quota

| Тип | Лимит | Хранение |
|-----|-------|----------|
| Аноним | `ANON_DAILY_LIMIT` (default 5) / день | Redis `quota:anon:{ip}:{date}`, TTL до полуночи |
| Free | `FREE_DAILY_LIMIT` (default 15) / день | Redis `quota:user:{pk}:{date}` |
| Premium | `PREMIUM_DAILY_LIMIT` (default 50) / день | то же |

### AI Quota

| Тип | Лимит | Хранение |
|-----|-------|----------|
| Аноним | `ANON_AI_DAILY_LIMIT` (default 3) / день | Redis `quota:anon_ai:{ip}:{date}` |
| Free | `FREE_AI_DAILY_LIMIT` (default 15) / день | Redis `quota:ai:user:{pk}:{date}` |
| Premium | `PREMIUM_AI_DAILY_LIMIT` (default 50) / день | то же |

**Троттлинг:** `SEARCH_THROTTLE_RATE=8` запросов/минуту на пользователя (по `user.pk`) или на IP. Скользящее окно 60с, Django cache (Redis).

**AI rate limit:** per-minute через `RedisRateLimiter` (`common/services/rate_limiter.py`) — ZSET sliding window.

**Глобальный Google cap:** `MAX_GOOGLE_CALLS_PER_DAY=500`, счётчик в Redis, сброс в полуночь.

---

## 🔐 Anti-abuse

**Cloudflare Turnstile** (backend-верификация через siteverify):
- логин (через `LoginGateMiddleware` + `google_oauth_start` view)
- удаление аккаунта
- контактная форма

**`ContactThrottleMiddleware`** (Django cache):
- аноним: 3 POST / 10 мин (по IP)
- авторизованный: 5 POST / 10 мин (по `user.pk`)

---

## ⭐ Favorites

Только для авторизованных пользователей.

- `Favorite` — снапшот данных дилера на момент добавления
- `POST /favorites/add/` — `get_or_create` по `(user, place_id)`
- `POST /favorites/remove/<place_id>/`
- `POST /favorites/clear/`
- `GET /favorites/` — список
- В search results: `is_favorite` флаг в контексте

---

## 📬 Contact

- `GET/POST /contact/` — форма (name, email, message)
- Turnstile верификация при POST
- Сохранение в `ContactMessage`
- Telegram-уведомление на каждое новое сообщение
- Email fallback если Telegram недоступен; ошибка уведомления не ломает запрос
- `ContactThrottleMiddleware` — см. Anti-abuse

---

## 🔎 Search Discovery

- **Popular cities:** `PopularSearch` инкрементируется при каждом поиске. Топ-10 на главной и в search view.
- **Search history:** авторизованные — `UserSearchHistory` (20 записей); анонимы — `session["search_history_cities"]` (8 городов, LIFO).
- `build_search_discovery_context(request)` — единая точка сборки для home и search view.

---

## 🤖 AI Integration

### Endpoints

| Метод | URL | Описание |
|-------|-----|----------|
| `GET` | `/dealer/{place_id}/ai-summary/` | Получить текущий AI-саммари (из кэша или БД) |
| `POST` | `/dealer/{place_id}/ai-summary/generate/` | Принудительно запустить генерацию (force=True) |

### Statuses

- `pending` — задача создана / в очереди
- `done` — успешно сгенерировано (свежее)
- `failed` — ошибка (с `error_code`): `system_quota_exceeded`, `quota_exceeded_anon`, `quota_exceeded_authenticated`, `quota_exceeded_premium`

### Enqueue logic (conservative mode, search flow)

Задача диспатчится только если: summary только создан | `done` + stalе | `failed` + retry cooldown прошёл | `pending` + stale (завис).

### Feature flags

`FEATURE_AI_SUMMARY_ENABLED` — включает/выключает AI-саммари в UI. Управляется через `common/services/feature_flags.py` (Redis).

---

## 📱 Frontend

Mobile-first: список дилеров → основной экран, карта → secondary, фильтры → offcanvas.

Autocomplete городов из `static/data/cities_de.json` (~3500 записей, генерируется `utils/build_cities.py`).

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

- web healthcheck через `/health/`
- db и redis healthchecks; переменные читаются из `.env`

`entrypoint.sh`: wait-for-redis → migrate → collectstatic → create superuser → configure Google SocialApp → start.

---

## Observability

- Structured JSON logging (`utils/logging.py` → `JsonFormatter`)
- Request-level logs через `RequestLoggingMiddleware` (path, method, status, duration_ms, user_id, client_ip)
- Domain events: `search_started`, `dealer_search_executed`, `search_quota_denied`, `ai_summary_task_dispatched`, `health_check_completed` и др.
- Health endpoint: `/health/` → DB + Redis checks, 200/503

---

## Cookie Consent / Privacy

- Cookie consent banner для third-party сервисов
- Consent хранится в session
- `/datenschutz/`, `/impressum/`, `/agb/` — статические legal pages (TemplateView)

---

## Testing

см. [testing.md](testing.md)

- `pytest-django` + `pytest-mock`
- Test settings: SQLite in-memory, `locmem.LocMemCache`
- `conftest.py`: autouse фикстура переопределяет CACHES на locmem

---

## Datenschutz / DSGVO

см. [legal_pages.md](legal_pages.md)

---

## Contacts

Author: Maksym Petrykin
Email: [m.petrykin@gmx.de](mailto:m.petrykin@gmx.de)
Telegram: [@max_p95](https://t.me/max_p95)