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
- [ ] Добавить `locationRestriction` с radius в payload
- [~] Добавить в FieldMask: `regularOpeningHours`, `currentOpeningHours`, `nationalPhoneNumber`, `websiteUri`, `types`
- [~] Нормализовать `open_now`, `opening_hours`, `types` в `normalize()`

## Auth + Rate Limiting
- [ ] Global cap: `MAX_GOOGLE_CALLS_PER_DAY` + fallback only-cache режим
- [ ] Чекбокс принятия AGB/Datenschutz при первом запросе (anon и при регистрации)
- [ ] Исправить сброс квоты при повторной авторизации через тот же Google-аккаунт — перед prod

## Anti-abuse
- [x] `integrations/turnstile.py` — верификация `cf-turnstile-response` через siteverify
- [ ] Проверять Turnstile ДО выполнения действия в `contact_view` и `delete_account_view`
- [ ] Подключить Turnstile на login flow

## Инфраструктура
- [ ] Redis в `docker-compose.yml`
- [ ] Gunicorn вместо `runserver` в production
- [ ] Nginx сервис в compose
- [ ] `depends_on` с `healthcheck` для db → web

## Шаблоны
- [x] Django Messages для: поиск, квота, auth, удаление (success/error/warning)
- [ ] Страницы: `/impressum`, `/datenschutz`, `/agb`
- [ ] Cookie banner (опциональные cookies: Google Maps, Google OAuth)

## Поиск
- [ ] Геолокация пользователя по клику на Search — показывать расстояние до дилера на карточке и в деталях
- [ ] Под кнопкой Search — уведомление о согласии с условиями использования и legal pages
- [ ] Учесть геолокацию в Datenschutz (обработка координат пользователя)

## Избранное
- [ ] Модель `Favorite` — привязка дилера к пользователю
- [ ] Страница `/favorites` — карточки в формате результатов поиска (вынести карточку в `includes`)
- [ ] Удаление отдельной карточки + очистить все (оба с подтверждением)
- [ ] Иконка звезды в навбаре
- [ ] Учесть хранение избранного в Datenschutz

## Тестирование
- [ ] Тесты для `QuotaMiddleware` и `ThrottleMiddleware`: сброс квоты при смене дня, превышение лимита, параллельные запросы, троттлинг по IP и по пользователю
- [ ] Тесты для `geocoding_service`: валидный немецкий город, невалидный город, город вне Германии, кэш-хит
- [ ] Тесты для `search_dealers`: cache HIT возвращает `from_cache=True`, cache MISS вызывает Google API и сохраняет в кэш
- [ ] Тесты для `contact_view`: успешная отправка сохраняет в БД, неполные данные возвращают warning
- [ ] Тесты для `delete_account_view`: удаление очищает User и связанные данные, redirect после удаления
- [ ] Тесты для `GoogleOAuthAdapter`: новый пользователь получает `plan=free`, существующий premium не откатывается в free

## Прочее
- [x] `STATIC_ROOT` в settings (для `collectstatic`)
- [x] `static/js/base.js`
- [x] Заполнить `README.md`
- [ ] `apps/dealers/selectors.py` — DB-запросы отдельно от сервисного слоя

## UX / Forms
- [ ] Ограничить количество символов в строке поиска до длины самого длинного названия населённого пункта в Германии
- [ ] Добавить live counter для поля поиска (`current / max`)
- [ ] Добавить suggestions/autocomplete населённых пунктов Германии при вводе в строке поиска
- [ ] Ограничить количество символов во всех полях формы обратной связи (`name`, `email`, `message`)
- [ ] Показать пользователю ошибки валидации длины полей до submit (client-side) и продублировать на backend

## Config / Security
- [ ] Вынести URL админки в `.env` (`ADMIN_URL`) и использовать в `config/urls.py`
- [ ] Убедиться, что `/admin/` не светится в production по умолчанию
- [ ] Проверять наличие всех обязательных env-переменных через единый config-layer

## Branding / Templates
- [ ] Добавить favicon
- [ ] Переопределить стандартные шаблоны `allauth` под единый UI проекта
- [ ] Добавить кастомные страницы ошибок `403`, `404`, `500`

## Notifications
- [ ] Отправлять уведомление в Telegram о новых `ContactMessage`
- [ ] Логировать неуспешную отправку Telegram-уведомления без падения запроса

## Validation / Hardening
- [ ] Валидировать `radius` на backend (min/max/allowed values), а не доверять input
- [ ] Нормализовать `city` before search: trim, collapse spaces, case normalization
- [ ] Защититься от пустых/мусорных запросов (`---`, 1 символ, только цифры)

## Search / Architecture
- [ ] Включить `radius` и фильтры в cache key, чтобы кэш соответствовал фактическому запросу
- [ ] Убрать двойной вызов `search_dealers()` в `search_view`
- [ ] Сначала валидировать город через geocoding, потом только вызывать search API