## 🧪 Testing

### Run all tests

```bash
pytest
```

### Run specific test modules

```bash
# Throttle middleware
pytest tests/tests_middleware.py

# OAuth start flow + login gate
pytest tests/tests_oauth_flow.py

# Frontend security / regression guards
pytest tests/tests_frontend_guards.py

# Dealer service
pytest tests/tests_dealer_service.py

# Geocoding
pytest tests/tests_geocoding.py

# Contact view
pytest tests/tests_contact_view.py
```

---

## Current coverage

| Area | File | Status |
|---|---|---|
| `ThrottleMiddleware` | `tests/tests_middleware.py` | ✅ |
| OAuth start flow (`google_oauth_start_view`) | `tests/tests_oauth_flow.py` | ✅ |
| OAuth direct access protection (`OAuthStartProtectionMiddleware`) | `tests/tests_oauth_flow.py` | ✅ |
| Frontend modal XSS regression guard | `tests/tests_frontend_guards.py` | ✅ |
| `geocoding_service` | `tests/tests_geocoding.py` | ✅ |
| `dealer_service` cache HIT / MISS | `tests/tests_dealer_service.py` | ✅ |
| `contact_view` | `tests/tests_contact_view.py` | ✅ |
| `delete_account_view` | not covered yet | ⏳ |
| `GoogleOAuthAdapter` | not covered yet | ⏳ |

---

## Throttle middleware test cases

Covered in `tests/tests_middleware.py`:

- requests within the configured rate are allowed
- request exceeding rate returns `429`
- authenticated users are throttled by `user.pk`, not by IP
- anonymous users are throttled by IP
- throttle resets after the next time window
- `REMOTE_ADDR` is used when `TRUST_X_FORWARDED_FOR=False`
- `X-Forwarded-For` is used when `TRUST_X_FORWARDED_FOR=True`
- non-search requests are ignored by the middleware

---

## OAuth flow test cases

Covered in `tests/tests_oauth_flow.py`:

- POST to `users:google_oauth_start` without valid Turnstile verification redirects back to login
- POST to `users:google_oauth_start` with valid Turnstile verification redirects to `google_login`
- session flag `google_oauth_verified` is set only after successful backend verification
- direct access to `google_login` without the session flag is blocked and redirected to `account_login`

---

## Frontend guard test cases

Covered in `tests/tests_frontend_guards.py`:

- `openDealerModal()` does not use `innerHTML`
- modal content is built through safe DOM APIs
- regression guard ensures the XSS fix is not accidentally reverted

---

## Notes

- `QuotaMiddleware` is no longer part of the runtime architecture. Quota handling now lives in the service layer (`apps.users.services.quota_service`), so middleware-based quota tests were removed.
- Test settings use SQLite in memory and `LocMemCache`.
- External integrations such as Google APIs and Turnstile should be mocked in tests.