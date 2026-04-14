## 🔁 Request Flow

### 🔍 Search

```
GET /search/?city=Berlin&radius=10
       ↓
ThrottleMiddleware — rate limit по user.pk / IP (Django cache, 60s time window)
       ↓
search_view
       ↓
quota_service — get_authenticated_quota_status() / get_anonymous_quota_status()
    → denied → 200 + warning message
       ↓
is_german_city() — Geocoding API (кэш 30 дней)
       ↓
search_dealers()
    → cache HIT  → return (data, from_cache=True)
    → cache MISS → Google Places API → normalize → sync_dealers_to_db() → set_cache() → return (data, False)
       ↓
Quota consume — только если cache MISS
       ↓
filter_and_sort_dealers() — in-memory фильтрация и сортировка
       ↓
enqueue_ai_summaries_for_dealers() — top-N дилеров в Celery (если AI_ENABLED)
       ↓
attach_ai_summaries_to_dealers() — прикрепить готовые AI-саммари к текущей странице
       ↓
Paginator (20/страница) → Template render
```

### 📍 Place Details

```
GET /dealer/{place_id}/ai-summary/       → get_dealer_ai_summary_payload() → JsonResponse
POST /dealer/{place_id}/ai-summary/generate/ → generate_dealer_ai_summary_payload() → JsonResponse
```

---