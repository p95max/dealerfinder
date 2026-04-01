# DealerFinder — v2 Checklist (AI Integration)

## 🎯 Goal

Добавить AI enrichment слой (review summary), не затрагивая core search logic.

- Core search logic остаётся полностью **детерминированной**
- AI используется только как **cached enrichment layer**
- AI не влияет на состав результатов и порядок выдачи
- Генерация summary выполняется **асинхронно**
- Summary отображается **только если уже готово**
- AI можно отключить через **feature flag**

---

## 🧱 Модели

- [ ] `Dealer`:
  - [ ] `ai_summary` (JSONField, nullable)
  - [ ] `ai_synced_at` (DateTimeField, nullable)
  - [ ] `ai_status` (`new | pending | ready | failed`, default=`new`)
  - [ ] `reviews_sample_count` (int, nullable)
  - [ ] `reviews_total_count_at_sync` (int, nullable)

---

## 🌍 Google Places — Place Details

- [ ] добавить `get_place_details(place_id)`
- [ ] использовать FieldMask:
  - `reviews`
  - `rating`
  - `userRatingCount`
  - `priceLevel`
  - `regularOpeningHours`
  - `currentOpeningHours`
  - `websiteUri`
  - `nationalPhoneNumber`
  - `types`

---

## 🤖 AI Service

- [ ] создать `apps/dealers/services/ai_service.py`

### Dealer context

- [ ] собирать `dealer_context` из Place Details:
  - name, rating, total_reviews
  - price_level
  - opening_hours
  - open_now
  - website, phone
  - types
  - reviews[]

### JSON contract (strict)

```json
{
  "positives": ["str"],
  "negatives": ["str"],
  "languages": ["str"],
  "export_friendly": bool,
  "warranty_mentions": bool,
  "tone": "positive | neutral | negative"
}
```

- [ ] без свободного текста
- [ ] обязательная валидация JSON
- [ ] fallback при невалидном ответе

### Правила

- [ ] если отзывов нет → AI не вызывается
- [ ] если отзывов < 3 → optional: не показывать summary или low-confidence режим
- [ ] избегать категоричных утверждений (fact claims)
- [ ] summary = signals, а не факты

---

## ⚙️ AI Job Flow (ASYNC)

- [ ] добавить task queue (Celery / RQ — на выбор)

### Задача

- [ ] `enrich_dealer_ai_summary(dealer_id)`

### Поведение

- [ ] запуск только если:
  - `ai_status is NULL` или `failed`
- [ ] не запускать если `ai_status = ready`

### Обработка

- [ ] retry policy
- [ ] timeout policy
- [ ] idempotency guard

### Статусы

- [ ] `pending` — задача запущена
- [ ] `ready` — summary готов
- [ ] `failed` — ошибка (не бесконечные ретраи)

---

## 💾 Cache & Strategy

- [ ] AI не вызывается повторно для дилеров со статусом `ready`
- [ ] для `failed` допускается ограниченный retry policy
- [ ] результат сохраняется в `Dealer.ai_summary`
- [ ] повторные запросы — только из БД

---

## 🔄 Интеграция в Search Flow (Resource-efficient)

### ❗ Scope v2

- [ ] AI summary отображается **только в search card**
- [ ] dealer detail page **НЕ входит в v2**
- [ ] AI используется как **background enrichment**, а не часть request flow

---

### 🚫 Ограничения (важно)

- [ ] НЕ вызывать AI синхронно в `search_view`
- [ ] НЕ запускать enrichment для всех дилеров подряд
- [ ] НЕ блокировать рендер страницы ожиданием AI

---

### ⚙️ Hybrid стратегия (экономный режим)

- [ ] после cache MISS сохраняем базовых дилеров
- [ ] запускать AI enrichment **только для top N результатов первой страницы** (например: 3–5)

- [ ] запуск enrichment:
  - [ ] асинхронно (task queue)
  - [ ] без ожидания результата в response

---

### 📦 Отображение (Eager if ready)

- [ ] `ai_summary` показывается **только если `ai_status = ready`**
- [ ] если `pending` → не показывать блок
- [ ] если `failed` → не показывать блок

- [ ] карточка дилера должна корректно рендериться **без AI блока**

---

### 🔁 Поведение при повторных запросах

- [ ] если `ai_status = ready` → всегда брать из БД
- [ ] повторно AI не вызывать

---

### 💸 Cost control

- [ ] ограничить количество enrichment задач (top N)
- [ ] не вызывать AI для дилеров вне первой страницы
- [ ] избегать повторных вызовов (idempotency)

---

### 🧠 Принцип

> Generation — async & selective  
> Display — eager if ready  
> No impact on search latency

---

## 🧩 UI / Templates

### dealer-card

- [ ] добавить AI summary блок
- [ ] показывать только если `ai_status = ready`

### Отображать

- [ ] positives
- [ ] negatives
- [ ] languages (если есть)

### Warning

- [ ] если `reviews_sample_count << reviews_total_count_at_sync`:
  - показывать:
  - "Summary based on a limited sample of recent reviews"

### UX

- [ ] UI не делает акцент на AI
- [ ] выглядит как “review insights”
- [ ] компактный блок

---

## 📄 Detail Page (опционально)

- [ ] подготовить future-ready использование AI summary

---

## ⚖️ Юридическое

- [ ] AI Disclaimer в `/agb`
- [ ] проверить необходимость в `/datenschutz`
- [ ] disclaimer под AI-блоком

### Важно

- [ ] избегать формулировок:
  - “работают с иностранцами”
  - “есть гарантия”
  - “честные цены”
- [ ] использовать мягкие формулировки:
  - “reviews mention…”
  - “customers report…”

---

## 🧪 Тесты

### Unit

- [ ] ai_service JSON validation
- [ ] no-reviews path
- [ ] invalid JSON fallback

### Logic

- [ ] skip if `ai_status = ready`
- [ ] skip if no reviews

### Integration

- [ ] search показывает summary если ready
- [ ] search не показывает если pending/failed

---

## 🚀 Future

- [ ] dealer detail page
- [ ] periodic re-sync (например раз в 30 дней)
- [ ] расширение JSON (confidence, tags)

---

## 🧠 Key Design Principle

Deterministic search + async cached AI enrichment