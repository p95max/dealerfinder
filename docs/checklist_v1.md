# DealerFinder — v1 Checklist

## Структура проекта
- [x] Разбить `settings.py` → `config/settings/base.py`, `dev.py`, `prod.py`
- [x] Создать `apps/users/` (User model, OAuth views)
- [ ] Создать `turnstile.py`

## Модели
- [ ] `Dealer`: добавить `opening_hours` (JSONField), `types` (JSONField)
- [ ] Создать `User` model: `google_sub`, `email`, `plan`, `daily_quota`, `used_today`, `last_quota_reset`
- [ ] DB-индексы: `city`, `lat`, `lng`, `last_synced_at`
- [ ] Сгенерировать и применить миграции

## Google Places API
- [ ] Добавить `locationBias` / `locationRestriction` с radius в payload
- [ ] Добавить в FieldMask: `regularOpeningHours`, `currentOpeningHours`, `nationalPhoneNumber`, `websiteUri`, `types`
- [ ] Нормализовать `open_now`, `opening_hours`, `types` в `normalize()`

## Auth + Rate Limiting
- [ ] Global cap: `MAX_GOOGLE_CALLS_PER_DAY` + fallback only-cache режим
- [ ] Чекбокс принятия AGB/Datenschutz при первом запросе от anon/при регистрации
- [ ] удаление аккаунта сбрасывает квоту: повторная авторизация через тот же Google-аккаунт создаёт нового User с `used_today=0`.

## Anti-abuse
- [ ] `integrations/turnstile.py` — верификация `cf-turnstile-response` через siteverify
- [ ] Подключить Turnstile на: регистрацию, логин, удаление аккаунта, контактная форма

## Инфраструктура
- [ ] Redis в `docker-compose.yml`
- [ ] Gunicorn вместо `runserver` в production
- [ ] Nginx сервис в compose
- [ ] `depends_on` с `healthcheck` для db → web

## Шаблоны
- [ ] Django Messages (`success/error/warning`) для: поиск, квота, auth, удаление
- [ ] Страницы: `/impressum`, `/datenschutz`, `/agb`
- [ ] Cookie banner (опциональные cookies: Google Maps, Google OAuth)

## Тестирование
- [ ] тесты для `QuotaMiddleware` и `ThrottleMiddleware`: сброс квоты при смене дня, превышение лимита, параллельные запросы, троттлинг по IP и по пользователю

## Прочее
- [x] `STATIC_ROOT` в settings (для `collectstatic`)
- [ ] `static/js/home.js`
- [ ] Заполнить `README.md`
- [ ] `apps/dealers/selectors.py` — DB-запросы отдельно от сервисного слоя

🔎 search:

* при нажатии на поиск идёт запрос к геолокации юзера, что б показать на каждом результате поиска(карточке) расстояния до него от юзера 
* показать это расстояние в dealer details
* учесть это в legal pages
* под кнопкой поиск добавить аккуратное сообщение что нажав эту кнопку пользователь соглашается с условиями пользования и legal pages

✴️ favorites (список карточек дилеров которые юзер пометил как избранное)

* формат карточки как в результатах поиска, возможно вынести ее в общий includes
* возможность быстро удалить каждую карточку + очистить все тоже, обе с предупреждением
* добавить закладку в навбар в виде звёзды 
* учесть этот раздел в legal pages

