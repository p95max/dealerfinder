## 🔁 Request Flow

### 🔍 Search

```
GET /search/?city=Berlin&radius=10
       ↓
ThrottleMiddleware — rate limit by user.pk / IP (Django cache, 60s time window)
       ↓
search_view
       ↓
quota_service — get_authenticated_quota_status() / get_anonymous_quota_status()
    → denied → 200 + warning message
       ↓
is_german_city() — Geocoding API (30-day cache)
       ↓
search_dealers()
    → cache HIT  → return (data, from_cache=True)
    → cache MISS → Google Places API → normalize → sync_dealers_to_db() → set_cache() → return (data, False)
       ↓
Quota consume — only on cache MISS
       ↓
filter_and_sort_dealers() — in-memory filtering and sorting
       ↓
enqueue_ai_summaries_for_dealers() — top-N dealers to Celery (if AI_ENABLED)
       ↓
attach_ai_summaries_to_dealers() — attach ready AI summaries to current page
       ↓
Paginator (20/page) → Template render
```

### 📍 Place Details

```
GET /dealer/{place_id}/ai-summary/       → get_dealer_ai_summary_payload() → JsonResponse
POST /dealer/{place_id}/ai-summary/generate/ → generate_dealer_ai_summary_payload() → JsonResponse
```

---