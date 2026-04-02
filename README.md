# DealerFinder

## 🧱 System Overview

`DealerFinder` — server-rendered Django-приложение для поиска автодилеров в Германии. Веб-система для поиска, фильтрации и структурированного
подбора сервисных организаций с использованием внешнего геоданных-провайдера и механизмов ограничения API-потребления

- Cache-first интеграция с Google Places API
- Поиск только по городам Германии (валидация через Geocoding API)
- Авторизация только через Google OAuth
- Anti-abuse: Cloudflare Turnstile + квоты + троттлинг

---

## 🏗️ Architecture

```
Client (Browser)
       ↓
   Middleware (QuotaMiddleware → ThrottleMiddleware → LoginGateMiddleware)
       ↓
Django Views (FBV)
       ↓
 Service Layer
 ├── Cache (PostgreSQL SearchCache / Redis)
 └── Google Places API
```

---

## 📁 Структура проекта

```
dealerfinder/
├── manage.py
├── build_cities.py          # one-time: генерирует static/data/cities_de.json
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
│   │   ├── services.py      # Telegram notify
│   │   ├── urls.py
│   │   └── views.py
│   │
│   ├── core/
│   │   ├── urls.py
│   │   └── views.py         # home, about, legal pages
│   │
│   ├── dealers/
│   │   ├── admin.py
│   │   ├── models.py        # Dealer, SearchCache, PopularSearch, UserSearchHistory
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── services/
│   │       ├── cache_service.py
│   │       ├── dealer_service.py
│   │       ├── distance_service.py
│   │       ├── geocoding_service.py
│   │       ├── google_places.py
│   │       └── search_tracking_service.py
│   │
│   └── users/
│       ├── admin.py
│       ├── middleware.py    # QuotaMiddleware, ThrottleMiddleware, LoginGateMiddleware
│       ├── models.py        # User, Favorite
│       ├── urls.py
│       └── views.py
│
├── integrations/
│   ├── google_oauth.py
│   ├── telegram.py
│   └── turnstile.py
│
├── utils/
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
QuotaMiddleware — проверка/сброс квоты (User или session для анонима)
       ↓
ThrottleMiddleware — rate limit по user.pk / IP
       ↓
search_view
       ↓
is_german_city() — Geocoding API (кэш 30 дней)
       ↓
search_dealers()
    → cache HIT  → return (data, from_cache=True)
    → cache MISS → Google Places API → normalize → set_cache → return (data, False)
       ↓
QuotaMiddleware (post-response) — инкремент только если cache MISS
       ↓
Template render
```

### 📍 Dealer details

```
GET /dealer/{id} → DB lookup → (optional) refresh if stale → render
```

---

## 🧠 Core Components

### Service Layer (`apps/dealers/services/`)

| Модуль | Ответственность |
|--------|----------------|
| `dealer_service.py` | оркестрация: cache → Google → normalize → store |
| `cache_service.py` | read/write `SearchCache` (TTL 24ч) |
| `google_places.py` | Text Search API, глобальный daily cap |
| `geocoding_service.py` | валидация города DE, кэш 30 дней |
| `distance_service.py` | haversine расстояние до пользователя |
| `search_tracking_service.py` | `PopularSearch`, `UserSearchHistory`, анон-история |

### Cache Strategy

| Параметр | Значение |
|----------|----------|
| Тип | read-through |
| Cache key | `dealers:{city}:{radius_int}` |
| TTL | 24 часа |
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
| `daily_quota` | int |
| `used_today` | int |
| `last_quota_reset` | **date** |
| `terms_accepted` | bool |

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

Фильтры и сортировка применяются **in-memory** после получения из кэша.

### Ранжирование

Комбинация факторов: weighted rating → наличие контактов → open_now бонус → расстояние.
Permissive filtering: если часы/выходные не заполнены — не исключается.

---

## ⚙️ Tech Stack

**Backend:** Python 3.12, Django 6.x (FBV), PostgreSQL 18.x, Redis

**Frontend:** Django Templates, Bootstrap 5.3, Vanilla JS

**External APIs:** Google Places API (New), Google Geocoding API, Geolocation API, Google OAuth, Telegram Bot API

**Infra:** Docker Compose v2, Gunicorn (2 workers), Nginx, Redis 7

---

## ⚡ Performance

- Cache-first, TTL 24ч
- FieldMask — только нужные поля от Google
- Place Details — только по клику, не в списке
- Геокодирование кэшируется 30 дней
- Пагинация: 20 результатов на страницу
- DB индексы: `city`, `lat`, `lng`, `last_synced_at`

---

## Auth

- Единственный способ — **Google OAuth** (`django-allauth`)
- `LoginGateMiddleware` — блокирует прямой переход на `/accounts/google/login/` без прохождения Turnstile
- При первом входе — обязательное принятие AGB/Datenschutz (`terms_accepted`)
- Анонимы — ограниченная квота через сессию
- Удаление аккаунта — каскадное удаление всех данных (DSGVO)
- ⚠️ Повторная авторизация через тот же Google-аккаунт после удаления создаёт нового User с `used_today=0` — исправить перед prod

---

## 💸 Cost Control

- Кэш — основной инструмент (TTL 24ч)
- FieldMask на всех запросах к Google
- Глобальный daily cap: `MAX_GOOGLE_CALLS_PER_DAY=500` → при достижении сервис работает только из кэша
- Квота списывается только за cache MISS
- Геокодирование кэшируется 30 дней

---

## Rate Limiting

| Тип | Лимит | Хранение |
|-----|-------|----------|
| Аноним | 3 / день | `session["anon_used"]`, сброс по дате |
| Free | 30 / день | `User.used_today`, `F()` atomic update |
| Premium | 200 / день | то же |

Квоты конфигурируются через `.env`: `ANON_DAILY_LIMIT`, `FREE_DAILY_LIMIT`, `PREMIUM_DAILY_LIMIT`.

**Троттлинг:** `SEARCH_THROTTLE_RATE=8` запросов/минуту на пользователя (по `user.pk`) или на IP (аноним). Скользящее окно 60с, in-memory.

**Глобальный cap:** `MAX_GOOGLE_CALLS_PER_DAY=500`, счётчик в Redis, сброс в полночь.

---

## 🔐 Anti-abuse

**Cloudflare Turnstile** (backend-верификация через siteverify):
- логин (через `LoginGateMiddleware` + `login_gate_view`)
- удаление аккаунта
- контактная форма

**`ContactThrottleMiddleware`** (Redis cache):
- аноним: 3 POST / 10 мин (по IP)
- авторизованный: 5 POST / 10 мин (по user.pk)

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
- Telegram-уведомление на каждое новое сообщение (ошибка отправки не ломает запрос)
- `ContactThrottleMiddleware` — см. Anti-abuse

---

## 🔎 Search Discovery

- **Popular cities:** `PopularSearch` инкрементируется при каждом поиске. Топ-10 на главной и в search view.
- **Search history:** авторизованные — `UserSearchHistory` (хранится 20 записей); анонимы — `session["search_history_cities"]` (8 городов, LIFO).
- `build_search_discovery_context(request)` — единая точка сборки для home и search view.

---

## 📱 Frontend

Mobile-first: список дилеров → основной экран, карта → secondary, фильтры → offcanvas.

Autocomplete городов из `static/data/cities_de.json` (~3500 записей, генерируется `build_cities.py`).

---

## 🔧 Deployment

```yaml
services:
  web    # Django + Gunicorn (2 workers)
  db     # PostgreSQL 18
  redis  # Redis 7
  nginx  # reverse proxy + static files
```

`entrypoint.sh`: migrate → collectstatic → createcachetable → create superuser → configure Google SocialApp → start.

---

## ⚠️ Tech Debt

см. [checklist_v1.md](checklist_v1.md)

---

## 🚀 Extensibility

- DRF / API layer
- Mobile client
- Celery (фоновые задачи)
- AI enrichment (v2, см. `docs/dealerfinder_ai_integration_v2.md`)

---

## 🤖 AI Integration

см. [dealerfinder_ai_integration_v2.md](dealerfinder_ai_integration_v2.md)

---

## Testing

см. [testing.md](testing.md)

---

## Datenschutz / DSGVO

см. [legal_pages.md](legal_pages.md)

---

## Contacts

Author: Maksym Petrykin
Email: [m.petrykin@gmx.de](mailto:m.petrykin@gmx.de)
Telegram: [@max_p95](https://t.me/max_p95)