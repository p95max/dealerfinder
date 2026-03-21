# DealerFinder — v1 Checklist

## Структура проекта
- [x] Разбить `settings.py` → `config/settings/base.py`, `dev.py`, `prod.py`
- [x] Создать `apps/users/` (User model, OAuth views)
- [ ] Создать `integrations/google_places.py`, `google_oauth.py`, `turnstile.py`
- [ ] Создать `common/` (constants, enums, exceptions, utils)
- [ ] Добавить `apps.py`, `admin.py` в `dealers`

## Модели
- [ ] `Dealer`: добавить `opening_hours` (JSONField), `types` (JSONField)
- [ ] Создать `User` model: `google_sub`, `email`, `plan`, `daily_quota`, `used_today`, `last_quota_reset`
- [ ] DB-индексы: `city`, `lat`, `lng`, `last_synced_at`
- [ ] Сгенерировать и применить миграции

## Google Places API
- [ ] Добавить `locationBias` / `locationRestriction` с radius в payload
- [ ] Добавить в FieldMask: `regularOpeningHours`, `currentOpeningHours`, `nationalPhoneNumber`, `websiteUri`, `types`
- [ ] Нормализовать `open_now`, `opening_hours`, `types` в `normalize()`

## Фильтры и ранжирование
- [x] `dealers/filters.py` — `open_now`, `weekends`, `types`, `contacts`
- [x] `dealers/scoring.py` — weighted rating (confidence-adjusted), бонус за контакты, `open_now`
- [x] Исправить cache key: `{city}_{radius}_{rating}_{open_now}_{weekends}_{contacts}`
- [x] Добавить фильтры в форму (`search_form.html`): open_now, weekends, contacts
- [x] Пагинация (20 на страницу)

## Auth + Rate Limiting
- [x] `integrations/google_oauth.py` — OAuth flow
- [x] `apps/users/views.py` — delete account
- [x] User profile
- [x] Middleware или decorator для квоты (`used_today >= daily_quota → LimitExceeded`)
- [x] Троттлинг: 5–10 req/min на пользователя
- [ ] Global cap: `MAX_GOOGLE_CALLS_PER_DAY` + fallback only-cache режим
- [ ] Чекбокс принятия AGB/Datenschutz при первом запросе

## Anti-abuse
- [ ] `integrations/turnstile.py` — верификация `cf-turnstile-response` через siteverify
- [ ] Подключить Turnstile на: регистрацию, логин, удаление аккаунта

## Инфраструктура
- [ ] Redis в `docker-compose.yml`
- [ ] Gunicorn вместо `runserver` в production
- [ ] Nginx сервис в compose
- [ ] `depends_on` с `healthcheck` для db → web

## Шаблоны
- [ ] Починить include в `home.html` (`dealers/search_form.html` → `includes/search_form.html`)
- [ ] Страница деталей дилера `/dealer/{id}` — view + template
- [ ] Django Messages (`success/error/warning`) для: поиск, квота, auth, удаление
- [ ] Страницы: `/impressum`, `/datenschutz`, `/agb`
- [ ] Cookie banner (опциональные cookies: Google Maps, Google OAuth)

## Прочее
- [ ] `STATIC_ROOT` в settings (для `collectstatic`)
- [ ] `static/js/home.js`
- [ ] Заполнить `README.md`
- [ ] `apps/dealers/selectors.py` — DB-запросы отдельно от сервисного слоя