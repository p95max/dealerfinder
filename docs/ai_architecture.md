# 🤖 AI Architecture

AI functionality is an **optional enrichment layer**, not a critical part of the system:

- AI summary is generated asynchronously via Celery + OpenAI
- The system is fully operational without AI (degrades gracefully)
- AI `can be disabled` via feature flag (`FEATURE_AI_SUMMARY_ENABLED`)
- Used only to improve UX (summaries, pros/cons, sentiment)

> ⚠️ Important: search, filtering, and result delivery are completely independent of AI.

## 🧠 Design Principles

- AI is optional and non-blocking
- Backend is the single source of truth
- Client handles only orchestration and UI updates
- AI results are cached and eventually consistent

---

## ⚡ Client-side AI handling (UX optimization)

Part of the AI logic is implemented on the client (JavaScript) to improve interface responsiveness.
The client contains no domain logic and does not affect data correctness.

Reasons:

- Reduced latency — UI is not blocked waiting for an AI response
- Async model — generation happens in the background (Celery), client only polls for status
- Immediate feedback — user sees `pending` state right away
- Less server load — no long-running HTTP requests

Client is responsible for:
- Triggering generation (`POST /ai-summary/generate/`)
- Fetching current state (`GET /ai-summary/`)
- Updating UI (pending → done / failed)

Server is responsible for:
- Queuing tasks
- Generating AI summary
- Caching and quota enforcement

> ⚠️ Important: business logic and AI generation remain entirely on the server.
> The client implements only orchestration and UI updates.

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

OneToOne to `Dealer` (related_name `ai_summary`). Created automatically on `sync_dealers_to_db`.

| Field | Type |
|-------|------|
| `status` | `pending` / `done` / `failed` |
| `provider`, `model`, `prompt_version` | str |
| `summary` | text |
| `pros`, `cons` | JSON array |
| `sentiment` | `positive` / `mixed` / `negative` \| blank |
| `languages` | JSON array |
| `export_friendly` | bool \| null |
| `confidence` | float \| null |
| `source_review_count` | int |
| `source_fingerprint` | str (SHA-64, idempotency) |
| `raw_response` | JSON \| null |
| `last_error` | text |
| `generated_at`, `updated_at` | datetime |

Freshness: `AI_SUMMARY_TTL_DAYS`. Retry failed: `AI_FAILED_RETRY_HOURS`. Stale pending: `AI_PENDING_STALE_MINUTES`.

---

## Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/dealer/{place_id}/ai-summary/` | Get current AI summary (from cache or DB) |
| `POST` | `/dealer/{place_id}/ai-summary/generate/` | Force-trigger generation (force=True) |

### Statuses

- `pending` — task created / queued
- `done` — successfully generated (fresh)
- `failed` — error (with `error_code`): `system_quota_exceeded`, `quota_exceeded_anon`, `quota_exceeded_authenticated`, `quota_exceeded_premium`

### Enqueue logic (conservative mode, search flow)

Task is dispatched only if: summary was just created | `done` + stale | `failed` + retry cooldown elapsed | `pending` + stale (hung).

### Feature flags

`FEATURE_AI_SUMMARY_ENABLED` — enables/disables AI summary in UI. Managed via `common/services/feature_flags.py` (Redis).

---

## ⚠️ Failure Behavior

- AI failures do not affect the main search
- On error, `failed` status is returned
- User can re-trigger generation manually
- System can auto-retry after cooldown expires