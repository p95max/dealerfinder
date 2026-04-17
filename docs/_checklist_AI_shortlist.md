# AI Shortlist

Режим ранжирования дилеров на основе отзывов и AI signals.  
Не меняет правила фильтрации, а только переупорядочивает результаты.

---

## UI

```
AI Shortlist
Quick picks based on real customer reviews

[ Most reliable ] [ Best value ] [ Lowest risk ] [ Export-friendly ]   (All results)
```

---

## План по спринтам

### [x] Sprint 0 — move LLM-related logic into `apps/dealers/ai/`
- [x] вынести low-level LLM logic в `apps/dealers/ai/`
- [x] prompts / parsers / client держать отдельно от business logic
- [x] orchestration оставить в `services/`

### [ ] Sprint 1 — UI + baseline scoring
- [ ] добавить `smart_pick` в search view
- [ ] вывести панель в UI, передавать режим через GET
- [ ] baseline scoring: `rating * log(review_count + 1)`

### [ ] Sprint 2 — deterministic scoring
- [ ] отдельные формулы для каждого режима
- [ ] детерминированная сортировка с tie-break по `id`
- [ ] unit tests для каждого режима

### [ ] Sprint 3 — AI signals
- [ ] `review_signal_service`: извлечение структурированных signals из отзывов
- [ ] cache в Redis: `ai_signals:{dealer_id}`, TTL 24h
- [ ] интеграция signals в `scoring.compute()`
- [ ] fallback на baseline scoring, если signals недоступны

### [ ] Sprint 4 — production hardening
- [ ] полный fallback при недоступности AI
- [ ] rate limiting для LLM API
- [ ] feature flag: `SMART_PICK_ENABLED`
- [ ] логирование: mode, latency, AI used / fallback used

### [ ] Sprint 5 — explainability (optional)
- [ ] `GET /dealers/{id}/shortlist-reason/?mode=...`
- [ ] UI: блок или tooltip “Why this dealer?”

---

## Правила

- Shortlist = sorting, а не filtering
- максимум 4–5 режимов
- `All results` всегда доступен
- AI используется только для извлечения signals
- scoring остаётся детерминированным
- fallback обязателен