## 🧪 Тестирование

### Запуск

```bash
# start all tests
pytest
```

```bash
# QuotaMiddleware & ThrottleMiddleware
pytest tests/tests_middleware.py
# dealer service 
pytest tests/tests_dealer_service.py
# geocoding 
pytest tests/tests_geocoding.py
```

### Покрытие

| Модуль | Файл | Статус |
|--------|------|-------|
| `QuotaMiddleware` | `apps/users/tests_middleware.py` | ✅ |
| `ThrottleMiddleware` | `apps/users/tests_middleware.py` | ✅ |
| `geocoding_service` | `apps/dealers/tests_geocoding.py` | [✅] |
| `dealer_service` (cache HIT/MISS) | `apps/dealers/tests_dealer_service.py` | [✅] |
| `contact_view` | `apps/dealers/tests_views.py` | [ ] |
| `delete_account_view` | `apps/users/tests_views.py` | [ ] |
| `GoogleOAuthAdapter` | `apps/users/tests_oauth.py` | [ ] |

### Тест-кейсы QuotaMiddleware
- сброс квоты при смене дня
- квота не сбрасывается в тот же день
- инкремент только при cache MISS
- cache HIT не тратит квоту
- превышение лимита блокирует запрос
- анонимный пользователь не отслеживается
- не-search запросы игнорируются
- параллельные запросы не пробивают лимит (атомарный `F()`)

### Тест-кейсы ThrottleMiddleware
- запросы в рамках лимита проходят
- превышение rate → 429
- авторизованные пользователи троттлятся по user.pk, не по IP
- анонимные пользователи троттлятся по IP
- `X-Forwarded-For` используется как источник IP
- истечение окна сбрасывает счётчик