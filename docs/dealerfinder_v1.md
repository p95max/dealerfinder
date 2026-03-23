# DealerFinder

## 🧱 System Overview

Сервис `DealerFinder` — это server-rendered веб-приложение, которое выполняет:

- поиск дилеров через Google Places API
- кэширование результатов
- отдачу данных через Django views
- отображение через шаблоны
- гибкая фильтрация найденых обьектов
- Anti-abuse Protection (Cloudflare Turnstile)
- авторизация только через Google OAuth (локальная регистрация по email/password не поддерживается)
- поиск дилеров только по городам Германии (валидация через Geocoding API)

Сервис реализует **cache-first** интеграцию с Google Places API, минимизируя внешние вызовы и стоимость, с простой server-side архитектурой и возможностью дальнейшего расширения через API слой.

---

## Фильтрация

> Поиск ограничен городами Германии. Запросы для других стран отклоняются на уровне сервиса.****

1. **radius** радиус поиска в км
2. **rating+reviews** связка 1. рейтинг (4+ / 4.5+) 2. количество отзывов(например: rating >= 4.3 AND user_ratings_total >= 20) 
* Примечание: Weighted rating / confidence-adjusted score: рейтинг должен ранжироваться с поправкой на количество отзывов, площадки с высоким средним рейтингом, но малым числом отзывов, не должны необоснованно попадать выше площадок со стабильным рейтингом и большим числом отзывов
3. **available now** открыто сейчас
4. **available on weekends** работает в выходные
5. **types** только Händler/Autohaus (жёстко через types тк фильтрация по слову в названии даст пропуски — легитимные дилеры называют себя "Auto Center", "KFZ München" и т.д.)
6. **contacts** имеет контакты (телефон, веб-сайт)

### Ранжирование (sorting)

**Цель - показывать наиболее надёжные и полезные площадки сверху**
Ранжирование должно учитывать комбинацию факторов:
- рейтинг (с поправкой на количество отзывов)
- наличие контактов (сайт / телефон)
- **available now** как бонус (не критичный фактор)
- расстояние до пользователя

#### Notes:
* Если рабочие часы либо работает в выходные нет, тогда есть → используется, если нет → не исключается(permissive filtering)
* Google Places часто даёт неполные данные - жёсткая фильтрация по часам → теряешь нормальные площадки важно не терять релевантные результаты.
* Обязательно избегать: - сортировку только по рейтингу; - сортировку только по расстоянию

---

## 🏗️ Architecture

```
Client (Browser)
       ↓
Django Views (FBV)
       ↓
 Service Layer
 ├── Cache (PostgreSQL / Redis)
 └── Google Places API
```

## MVP-структура

dealermap/
├── manage.py
├── .env.example
├── .gitignore
├── README.md
│
├
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
├
├── config/
│   ├── __init__.py
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py
│       ├── dev.py
│       └── prod.py
│
├── apps/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── tests.py
│   │   └── templates/
│   │       └── core/
│   │           ├── home.html
│   │           └── about.html
│   │
│   ├── users/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── admin.py
│   │   ├── models.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── services.py
│   │   ├── selectors.py
│   │   ├── tests.py
│   │   └── migrations/
│   │
│   └── dealers/
│       ├── __init__.py
│       ├── apps.py
│       ├── admin.py
│       ├── models.py
│       ├── urls.py
│       ├── views.py
│       ├── services.py
│       ├── selectors.py
│       ├── filters.py
│       ├── scoring.py
│       ├── tests.py
│       └── migrations/
│
├── integrations/
│   ├── __init__.py
│   ├── google_places.py
│   ├── google_oauth.py
│   └── turnstile.py
│
├── common/
│   ├── __init__.py
│   ├── constants.py
│   ├── enums.py
│   ├── exceptions.py
│   └── utils.py
│
├── templates/
│   ├── base.html
│   └── includes/
│       ├── navbar.html
│       ├── footer.html
│       └── messages.html
│
└── static/
    ├── css/
    │   └── home.css
    ├── js/
    │   └── home.js
    └── img/
 
- менеджер зависимовстей Poetry последней версии
- в /static скрипты для каждой статической страницы отдельными файлами
- никаких ИИ комментариев в коде, только docstring в ключевых местах 
 
---

## 🔁 Request Flow

### 🔍 Search flow

```
User → /search?city=Berlin&radius=10
       ↓
      View
       ↓
   Geocoding API → валидация города (DE only)
       ↓
 Service layer:
     → check cache
         → HIT  → return cached data
         → MISS → call Google API
                      ↓
                   normalize data
                      ↓
                   save to DB
                      ↓
                   return response
       ↓
 Template render
```

### 📍 Dealer details flow

```
User → /dealer/{id}
       ↓
      View
       ↓
   DB lookup
       ↓
 (optional) refresh from Google if stale
       ↓
 render template
```

---

## 🧠 Core Components

### 1. Service Layer _(ключевой слой)_

Отвечает за:

- интеграцию с Google API
- кэширование
- нормализацию данных
- бизнес-логику

Структура:

```
services/
├── google_places.py
├── dealer_service.py
├── cache_service.py
└── geocoding_service.py
```

### 2. Cache Strategy

| Параметр  | Значение                                                           |
|-----------|--------------------------------------------------------------------|
| Тип       | read-through cache                                                 |
| Cache key | `{city}_{radius}_{type}_{rating}_{open_now}_{weekends}_{contacts}` |
| TTL       | 24 часа                                                            |
| HIT       | сразу возврат                                                      |
| MISS      | запрос в Google → запись в БД                                      |

### 3. Data Normalization

Google → внутренний формат:

```json
{
  "name":     "str",
  "address":  "str",
  "lat":      "float",
  "lng":      "float",
  "rating":   "float",
  "place_id": "str",
  "website":  "str | None"
}
```

---

## 🗄️ Data Storage

### `Dealer`

| Поле                | Тип      |
|---------------------|----------|
| `google_place_id`   | unique   |
| `name`              | str      |
| `address`           | str      |
| `city`              | str      |
| `lat`, `lng`        | float    |
| `rating`            | float    |
| `user_ratings_total`| int      |
| `website`           | str      |
| `phone`             | str      |
| `opening_hours`     | json     |
| `last_synced_at`    | datetime |

### `SearchCache`

| Поле           | Тип      |
|----------------|----------|
| `query_key`    | str      |
| `results_json` | json     |
| `created_at`   | datetime |

### `User`

| Поле               | Тип      |
|--------------------|----------|
| `created_at`       | datetime |
| `updated_at`       | datetime |
| `google_sub`       | str      |
| `email`            | str      |
| `plan`             | str      |
| `daily_quota`      | int      |
| `used_today`       | int      |
| `last_quota_reset` | datetime |

---

## ⚙️ Tech Stack

### Backend

- Python 3.12
- Django 6.x (FBV)
- Django Messages Framework — flash-уведомления (success / error / warning)
  для операций: поиск, лимит квоты, авторизация, удаление аккаунта
- PostgreSQL 18.х
- Cloudflare Turnstile 

### Frontend

- Django Templates
- Bootstrap 5.3
- Vanilla JS

### External APIs

- Google Places API (New)
- Google Geocoding API
- Geolocation API

- Google Auth

### Infra

- Docker Compose v2
- Gunicorn
- Nginx 
- Redis

---

## ⚡ Performance Strategy

- cache-first approach
- минимальный набор полей (FieldMask)
- lazy loading деталей (по клику)
- отказ от realtime обновлений
- оптимизация запросов в БД (индексы на `city`, `lat`, `lng`, `last_synced_at`)
- пагинация: 20 результатов на страницу.

---

## Auth

- единственный способ авторизации — **Google OAuth** (локальная регистрация не поддерживается)
- доступ к поиску и регистрация требуют явного принятия **AGB и Datenschutz** (чекбокс при первом запросе)
- без принятия соглашения поиск и регистрация недоступны
- анонимные пользователи работают с ограниченной квотой (см. `Rate Limiting`)
- авторизованные пользователи получают расширенную квоту и доступ к персональному разделу
- все защищённые endpoint'ы требуют авторизацию
- удаление аккаунта и всех связанных данных — обязательная функция (требование DSGVO)
- удаление аккаунта сбрасывает квоту: повторная авторизация через тот же Google-аккаунт создаёт нового User с `used_today=0`. Исправить перед prod.

---

## 💸 Cost Control

- агрессивное кэширование (TTL 24ч) — основной инструмент
- FieldMask — запрашивать только нужные поля у Google API
- отключение дорогих endpoints (Place Details только по клику, не в списке)
- глобальный daily cap: `MAX_GOOGLE_CALLS_PER_DAY = 500`
  - при достижении: сервис работает только из кэша, новые запросы к Google не идут
- квота списывается только за cache MISS — повторные поиски из кэша бесплатны
- результаты геокодирования кэшируются на 30 дней — невалидные города не тарифицируются повторно

##  Rate Limiting

```python
if user.used_today >= user.daily_quota:
    raise LimitExceeded
```


| Тип          | Лимит      | Цель                                   |
|--------------|------------|----------------------------------------|
| Аноним       | 05 / день  | дать почувствовать ценность            |
| Free (зарег) | 30 / день  | удержать, показать что сервис работает |
| Прем         | 500 / день | fair use, без видимого лимита         |

Дополнительно:

- глобальный лимит запросов к Google API
- fallback → только кэш
- троттлинг: 5–10 запросов / минута на пользователя

---

### 🔐 Anti-abuse Protection

**Cloudflare Turnstile используется для защиты от ботов для форм:**
- регистрация
- логин
- удаление аккаунта

* Проверка выполняется на backend: токен cf-turnstile-response обязателен для проверки через siteverify API - `запрос без валидного токена отклоняется`
* Anonymous → всегда проверка, Free → проверка при превышении X запросов, Premium → без Turnstile но может включаться при подозрительном поведении (rate spikes, частые уникальные запросы)

---

## 🤖 AI Integration (enrichment layer)

см. [ai_integration.md](ai_integration.md)

---


## 📱 Frontend Behavior

Mobile-first:
- список дилеров → основной экран
- карта → secondary view
- фильтры → offcanvas

---

## 🔧 Deployment

```yaml
# Docker Compose services
- web   # Django
- db    # PostgreSQL
- redis 
```

---

## ⚠️ Tech Debt

> **search_view:** фильтрация и сортировка в памяти после search_dealers() — перенести в DB-запрос или на уровень сервиса при росте объёма
> **ThrottleMiddleware** использует in-memory store — не работает корректно при нескольких Gunicorn workers или перезапуске контейнера. Заменить на Redis перед prod (при переходе на Gunicorn + Nginx).
> отсутствуют тесты для `QuotaMiddleware` и `ThrottleMiddleware`: сброс квоты при смене дня, превышение лимита, параллельные запросы, троттлинг по IP и по пользователю

---

## 🚀 Extensibility

- DRF / API layer
- mobile client
- background jobs (Celery)
- enrichment данных дилеров

---

## Datenschutz (DSGVO)/Nutzervereinbarung 

см. [legal_pages.md](legal_pages.md)

--- 

## Contacts

Author: Maksym Petrykin
Email: [m.petrykin@gmx.de](mailto:m.petrykin@gmx.de)
Telegram: [@max_p95](https://t.me/max_p95)

---


