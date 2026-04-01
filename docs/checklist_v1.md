# DealerFinder — v1 Checklist

## Структура проекта
- [x] Разбить `settings.py` → `config/settings/base.py`, `dev.py`, `prod.py`
- [x] Создать `apps/users/` (User model, OAuth views)
- [x] Создать `integrations/turnstile.py`

## Модели
- [x] `Dealer`: добавить `opening_hours` (JSONField), `types` (JSONField)
- [x] DB-индексы: `city`, `lat`, `lng`, `last_synced_at`
- [x] Сгенерировать и применить миграции

## Google Places API
- [x] Добавить `locationRestriction` с radius в payload
- [x] Добавить в FieldMask: `regularOpeningHours`, `currentOpeningHours`, `nationalPhoneNumber`, `websiteUri`, `types`
- [x] Нормализовать `open_now`, `opening_hours`, `types` в `normalize()`

## Auth + Rate Limiting
- [x] Global cap: `MAX_GOOGLE_CALLS_PER_DAY` + fallback only-cache режим
- [x] Чекбокс принятия AGB/Datenschutz при первом запросе (anon и при регистрации)

## Anti-abuse
- [x] `integrations/turnstile.py` — верификация `cf-turnstile-response` через siteverify
- [x] Проверять Turnstile ДО выполнения действия в `contact_view` и `delete_account_view`
- [x] Подключить Turnstile на login flow

## Инфраструктура
- [x] Redis в `docker-compose.yml`
- [x] Gunicorn вместо `runserver` в production
- [x] Nginx сервис в compose
- [x] `depends_on` с `healthcheck` для db → web

## Шаблоны
- [x] Django Messages для: поиск, квота, auth, удаление (success/error/warning)
- [x] Страницы: `/impressum`, `/datenschutz`, `/agb`
- [x] Cookie banner (опциональные cookies: Google Maps, Google OAuth)

## Поиск
- [x] Геолокация пользователя по клику на Search — показывать расстояние до дилера на карточке и в деталях
- [x] Под кнопкой Search — уведомление о согласии с условиями использования и legal pages

## Избранное
- [x] Модель `Favorite` — привязка дилера к пользователю
- [x] Страница `/favorites` — карточки в формате результатов поиска (вынести карточку в `includes`)
- [x] Удаление отдельной карточки + очистить все (оба с подтверждением)
- [x] Иконка звезды в навбаре

## Тестирование
- [x] Тесты для `QuotaMiddleware` и `ThrottleMiddleware`: сброс квоты при смене дня, превышение лимита, параллельные запросы, троттлинг по IP и по пользователю
- [x] Тесты для `geocoding_service`: валидный немецкий город, невалидный город, город вне Германии, кэш-хит
- [x] Тесты для `search_dealers`: cache HIT возвращает `from_cache=True`, cache MISS вызывает Google API и сохраняет в кэш
- [x] Тесты для `contact_view`: успешная отправка сохраняет в БД, неполные данные возвращают warning
- [ ] Тесты для `delete_account_view`: удаление очищает User и связанные данные, redirect после удаления
- [ ] Тесты для `GoogleOAuthAdapter`: новый пользователь получает `plan=free`, существующий premium не откатывается в free

## Прочее
- [x] `STATIC_ROOT` в settings (для `collectstatic`)
- [x] `static/js/base.js`
- [x] Заполнить `README.md`

## UX / Forms
- [x] Ограничить количество символов в строке поиска до длины самого длинного названия населённого пункта в Германии
- [x] Добавить live counter для поля поиска (`current / max`)
- [x] Добавить suggestions/autocomplete населённых пунктов Германии при вводе в строке поиска
- [x] Ограничить количество символов во всех полях формы обратной связи (`name`, `email`, `message`)
- [x] Показать пользователю ошибки валидации длины полей до submit (client-side) и продублировать на backend

## Config / Security
- [x] Вынести URL админки в `.env` (`ADMIN_URL`) и использовать в `config/urls.py`
- [x] Убедиться, что `/admin/` не светится в production по умолчанию
- [x] Проверять наличие всех обязательных env-переменных через единый config-layer

## Branding / Templates
- [x] Добавить favicon
- [x] Переопределить стандартные шаблоны `allauth` под единый UI проекта
- [X] Добавить кастомные страницы ошибок `403`, `404`, `500`

## Validation / Hardening
- [x] Валидировать `radius` на backend (min/max/allowed values), а не доверять input
- [x] Нормализовать `city` before search: trim, collapse spaces, case normalization
- [x] Защититься от пустых/мусорных запросов (`---`, 1 символ, только цифры)

## Search / Architecture
- [x] Включить `radius` и фильтры в cache key, чтобы кэш соответствовал фактическому запросу
- [x] Убрать двойной вызов `search_dealers()` в `search_view`
- [x] Сначала валидировать город через geocoding, потом только вызывать search API

## Notifications
- [x] Отправлять уведомление в Telegram о новых `ContactMessage`
- [x] Логировать неуспешную отправку Telegram-уведомления без падения запроса

# Other
- [x] Заполнить Legal pages под текущий билд