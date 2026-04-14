# 🤖 AI Architecture

AI-функциональность является **необязательным слоем обогащения**, а не критической частью системы:

- AI summary генерируется асинхронно через Celery + OpenAI
- система полностью работоспособна без AI (degrades gracefully)
- AI `может быть отключён` через feature flag (`FEATURE_AI_SUMMARY_ENABLED`)
- используется только для улучшения UX (summaries, pros/cons, sentiment)

> ⚠️ Важно: поиск, фильтрация и выдача результатов полностью независимы от AI.

## 🧠 Design Principles

- AI is optional and non-blocking
- backend is the single source of truth
- client handles only orchestration and UI updates
- AI results are cached and eventually consistent

---

## ⚡ Client-side AI handling (UX optimization)

Часть AI-логики реализована на клиенте (JavaScript) для улучшения отзывчивости интерфейса.
Клиент не содержит доменной логики и не влияет на корректность данных.

Причины:

- снижение latency — UI не блокируется ожиданием AI-ответа
- асинхронная модель — генерация происходит в фоне (Celery), клиент лишь опрашивает состояние
- мгновенная обратная связь — пользователь сразу видит `pending` состояние
- меньше нагрузки на сервер — нет долгих HTTP-запросов

Клиент отвечает за:
- триггер генерации (`POST /ai-summary/generate/`)
- получение текущего состояния (`GET /ai-summary/`)
- обновление UI (pending → done / failed)

Сервер отвечает за:
- постановку задач в очередь
- генерацию AI summary
- кэширование и контроль квот

> ⚠️ Важно: бизнес-логика и генерация AI полностью остаются на сервере.
> Клиент реализует только orchestration и UI-обновление.

---

## 🤖 AI Summary (Celery)

```
generate_dealer_ai_summary_task.delay(place_id)
       ↓
acquire_ai_summary_lock()
       ↓
get_place_details()  # Redis cache + lock around Place Details
       ↓
build AI context + validate review availability
       ↓
freshness / retry / fingerprint checks
       ↓
check AI quota (per-user/IP + system cap)
       ↓
OpenAI API
       ↓
DealerAiSummary.save(status=done/failed)
       ↓
invalidate cached payload
       ↓
release_ai_summary_lock()
```

---

## `DealerAiSummary`

OneToOne к `Dealer` (related_name `ai_summary`). Создаётся автоматически при `sync_dealers_to_db`.

| Поле | Тип |
|------|-----|
| `status` | `pending` / `done` / `failed` |
| `provider`, `model`, `prompt_version` | str |
| `summary` | text |
| `pros`, `cons` | JSON array |
| `sentiment` | `positive` / `mixed` / `negative` \| blank |
| `languages` | JSON array |
| `export_friendly` | bool \| null |
| `confidence` | float \| null |
| `source_review_count` | int |
| `source_fingerprint` | str (SHA-64, идемпотентность) |
| `raw_response` | JSON \| null |
| `last_error` | text |
| `generated_at`, `updated_at` | datetime |

Freshness: `AI_SUMMARY_TTL_DAYS`. Retry failed: `AI_FAILED_RETRY_HOURS`. Stale pending: `AI_PENDING_STALE_MINUTES`.

---

## Endpoints

| Метод | URL | Описание |
|-------|-----|----------|
| `GET` | `/dealer/{place_id}/ai-summary/` | Получить текущий AI-саммари (из кэша или БД) |
| `POST` | `/dealer/{place_id}/ai-summary/generate/` | Принудительно запустить генерацию (force=True) |

### Statuses

- `pending` — задача создана / в очереди
- `done` — успешно сгенерировано (свежее)
- `failed` — ошибка (с `error_code`): `system_quota_exceeded`, `quota_exceeded_anon`, `quota_exceeded_authenticated`, `quota_exceeded_premium`

### Enqueue logic (conservative mode, search flow)

Задача диспатчится только если: summary только создан | `done` + stalе | `failed` + retry cooldown прошёл | `pending` + stale (завис).

### Feature flags

`FEATURE_AI_SUMMARY_ENABLED` — включает/выключает AI-саммари в UI. Управляется через `common/services/feature_flags.py` (Redis).

---

## ⚠️ Failure Behavior

- AI failures не влияют на основной поиск
- при ошибке возвращается статус `failed`
- пользователь может повторно инициировать генерацию
- система может автоматически ретраить при истечении cooldown

