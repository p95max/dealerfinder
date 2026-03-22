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
- [ ] Чекбокс принятия AGB/Datenschutz при первом запросе от anon/при регистрации
- [ ] удаление аккаунта сбрасывает квоту: повторная авторизация через тот же Google-аккаунт создаёт нового User с `used_today=0`.

## Anti-abuse
- [ ] `integrations/turnstile.py` — верификация `cf-turnstile-response` через siteverify
- [ ] Подключить Turnstile на: регистрацию, логин, удаление аккаунта

## Инфраструктура
- [ ] Redis в `docker-compose.yml`
- [ ] Gunicorn вместо `runserver` в production
- [ ] Nginx сервис в compose
- [ ] `depends_on` с `healthcheck` для db → web

## Шаблоны
- [x] Починить include в `home.html` (`dealers/search_form.html` → `includes/search_form.html`)
- [ ] Страница деталей дилера `/dealer/{id}` — view + template
- [ ] Django Messages (`success/error/warning`) для: поиск, квота, auth, удаление
- [ ] Страницы: `/impressum`, `/datenschutz`, `/agb`
- [ ] Cookie banner (опциональные cookies: Google Maps, Google OAuth)

## Прочее
- [x] `STATIC_ROOT` в settings (для `collectstatic`)
- [ ] `static/js/home.js`
- [ ] Заполнить `README.md`
- [ ] `apps/dealers/selectors.py` — DB-запросы отдельно от сервисного слоя

ℹ️ dealer details: 

* модальное окно с подробной инфой о дилере 
* миникарта с меткой
* заложить область для summary обзора отзывов от LLM.
* кнопки проложить маршрут и поделиться дилером (отправить на емайл, скопировать инфу в буфер обмена)
* добавить ссылку в навбар 

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

- About us (современная страница о сервисе)
* добавить ссылку в навбар
* описать суть и назначение сервиса- быстрый и удобный поиск автодилеров в Германии с фильтрами и личным разделом и закладками.
* описать фичи сервиса 

🔗 Contact (2 карточки где форма это 1я, и контакты 2я)
* форма обратной связи с полями имя, емайл и суть вопроса 
* защита формы Claudfire, только после проверки кнопка отправить стает доступна, продумать таймаут на отправку вопросов
* во 2й карточке контактый емайл и телеграм
* учесть обработку личных данных через форму в Datenschutz 
* добавить ссылку в навбар

🔖Navbar
* оживить кнопки навбара
* при переходе на стр навбара под светить стр на какой находимся