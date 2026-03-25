# DealerFinder — v1 Checklist

## Структура проекта
- [x] Разбить `settings.py` → `config/settings/base.py`, `dev.py`, `prod.py`
- [x] Создать `apps/users/` (User model, OAuth views)
- [x] Создать `integrations/turnstile.py`

## Модели
- [ ] `Dealer`: добавить `opening_hours` (JSONField), `types` (JSONField)
- [ ] DB-индексы: `city`, `lat`, `lng`, `last_synced_at`
- [ ] Сгенерировать и применить миграции

## Google Places API
- [ ] Добавить `locationRestriction` с radius в payload
- [ ] Добавить в FieldMask: `regularOpeningHours`, `currentOpeningHours`, `nationalPhoneNumber`, `websiteUri`, `types`
- [ ] Нормализовать `open_now`, `opening_hours`, `types` в `normalize()`

## Auth + Rate Limiting
- [ ] Global cap: `MAX_GOOGLE_CALLS_PER_DAY` + fallback only-cache режим
- [ ] Чекбокс принятия AGB/Datenschutz при первом запросе (anon и при регистрации)
- [ ] Исправить сброс квоты при повторной авторизации через тот же Google-аккаунт — перед prod

## Anti-abuse
- [x] `integrations/turnstile.py` — верификация `cf-turnstile-response` через siteverify
- [x] Подключить Turnstile на: логин, удаление аккаунта, контактную форму

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