# DealerFinder — AI Gap Closure Checklist

## Sprint 1 — Архитектурный долг (CRITICAL)  `CLOSED`
- [x] Remove synchronous AI generation from `dealer_ai_summary_view`  
  → Make endpoint read-only

- [x] Add background job enqueue in `search_view()` (top N dealers on cache MISS)  
  → Trigger async summary generation

- [x] Introduce `AI_SYNC_LIMIT` in settings  
  → Control number of dealers processed per request

- [x] Implement `pending` state response in API  
  → Return status instead of blocking request

- [x] Add job status model (`pending`, `done`, `failed`)  
  → Ensure visibility and control over async processing

---

## Sprint 2 — Cost Control & Stability
- [ ] Add AI quota (per user, daily limit)  
  → Prevent abuse and uncontrolled API costs

- [ ] Display “AI summaries today” in profile/navbar  
  → Increase transparency for users

- [ ] Implement anti-spam guard (user-level + system-level)  
  → Rate limit failed/pending job creation

- [ ] Add retry logic for failed jobs  
  → Avoid permanent broken states

---

## Sprint 3 — Data Correctness / UX / Legal
- [ ] Add `reviews_total_count_at_sync` field  
  → Detect stale summaries

- [ ] Implement “limited sample” warning  
  → Show when data is insufficient

- [ ] Add AI disclaimer in runtime (AGB / UI)  
  → Inform user about generated content

- [ ] Update Datenschutz for AI processing  
  → Cover external API data transfer

- [ ] Add periodic re-sync scheduler  
  → Keep summaries актуальными

- [ ] Implement stale detection logic  
  → Regenerate if data outdated

---

## Sprint 4 — Product Improvements (Optional)
- [ ] Build full dealer detail page  
  → Central place for dealer info + AI summary

- [ ] Add `tags` to AI JSON response  
  → Enable filtering and UX improvements

- [ ] Add fallback UI for missing summaries  
  → Improve resilience

---

## Notes
- Sprint 1 is blocking release (must-have)
- Sprint 2 protects from financial risk
- Sprint 3 required for compliance (Germany / DSGVO)
- Sprint 4 is product polish