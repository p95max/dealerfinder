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

- [x] `Dealer`:
  - `ai_summary` (JSONField, nullable) — *(реализовано через отдельную модель `DealerAiSummary` OneToOne)*
  - `ai_synced_at` (DateTimeField, nullable) — *(`generated_at` в `DealerAiSummary`)*
  - `ai_status` (`new | pending | ready | failed`, default=`new`) — *(`pending | done | failed` в `DealerAiSummary`)*
  - `reviews_sample_count` (int, nullable) — *(`source_review_count` в `DealerAiSummary`)*
  - `reviews_total_count_at_sync` (int, nullable) — *не реализовано*

---

## 🌍 Google Places — Place Details

- [x] добавить `get_place_details(place_id)`
- [x] использовать FieldMask:
  - [x] `reviews`
  - [x] `rating`
  - [x] `userRatingCount`
  - [x] `priceLevel`
  - [x] `regularOpeningHours`
  - [x] `currentOpeningHours`
  - [x] `websiteUri`
  - [x] `nationalPhoneNumber`
  - [x] `types`

---

## 🤖 AI Service

- [x] создать `apps/dealers/services/dealer_ai_service.py`

### Dealer context

- [x] собирать `dealer_context` из Place Details:
  - [x] name, rating, total_reviews
  - [x] price_level
  - [x] opening_hours
  - [x] open_now
  - [x] website, phone
  - [x] types
  - [x] reviews[]

### JSON contract (strict)

> ⚠️ Реализованный контракт отличается от чеклиста:
```json
{
  "pros": ["str"],
  "cons": ["str"],
  "languages": ["str"],
  "export_friendly": bool,
  "sentiment": "positive | mixed | negative",
  "confidence": 0.0-1.0,
  "summary": "str"
}
```

- [x] без свободного текста *(есть `summary` поле)*
- [x] обязательная валидация JSON
- [x] fallback при невалидном ответе

### Правила

- [x] если отзывов нет → AI не вызывается

---

### Поведение

- [x] запуск только если `ai_status != done` (idempotency через fingerprint)
- [x] не запускать если `status = done`

### Обработка

- [ ] retry policy *(нет ретраев в task, есть в HTTP-запросах)*
- [x] timeout policy *(`AI_REQUEST_TIMEOUT` в settings)*
- [x] idempotency guard *(fingerprint-based)*

### Статусы

- [x] `pending` — задача запущена
- [x] `done` (≠ `ready`) — summary готов
- [x] `failed` — ошибка

---

## 💾 Cache & Strategy

- [x] AI не вызывается повторно для дилеров со статусом `done`
- [ ] для `failed` допускается ограниченный retry policy *(нет ограничения на ретраи failed)*
- [x] результат сохраняется в `DealerAiSummary`
- [x] повторные запросы — только из БД
- [x] Сделать persistent cache в БД + TTL.
Хранение в Dealer:
`ai_summary
ai_summary_status
ai_summary_generated_at
`
И правила:
`
если summary есть и ему меньше 7 дней → отдаём из БД
если summary старше 7 дней → генерим заново
если summary пустой или failed → пробуем снова
`
**Это проще, чем городить отдельный in-memory кеш или Redis только ради summary.**

---

## 🔄 Интеграция в Search Flow

### ❗ Scope v2

- [x] AI summary отображается только в search card
- [x] dealer detail page — отдельная страница (modal)
- [x] AI используется как background enrichment

---

### 🚫 Ограничения

- [x] НЕ запускать enrichment для всех дилеров подряд *(top 5 через `AI_SYNC_LIMIT=5`)*
- [x] НЕ блокировать рендер страницы ожиданием AI *(условно: inline sync может блокировать)*

---

### ⚙️ Hybrid стратегия

- [x] после cache MISS сохраняем базовых дилеров
- [x] запускать AI enrichment только для top N результатов (`AI_SYNC_LIMIT=5`)
- [ ] запуск enrichment асинхронно (task queue)
- [ ] без ожидания результата в response 

---

### 📦 Отображение (Eager if ready)

- [x] `ai_summary` показывается только если `ai_status = done`
- [x] если `pending` → не показывать блок
- [x] если `failed` → не показывать блок
- [x] карточка дилера корректно рендериться без AI блока

---

### 🔁 Поведение при повторных запросах

- [x] если `status = done` → брать из БД
- [x] повторно AI не вызывать

---

### 💸 Cost control

- [x] ограничить количество enrichment задач (top N = 5)
- [x] не вызывать AI для дилеров вне первой страницы
- [x] избегать повторных вызовов (idempotency через fingerprint)
- [ ] установить `дневной лимит AI summary`: anon - 5 шт. , free - 15 шт., premium - 50 шт.
 * Чесно лимитировать не “просмотры AI summary”, а именно: новые генерации AI summary, которые реально вызвали AI provider`
 * Показать пользователю отдельный счётчик типа AI summaries today в User Profile + Dropdown menu
 * не смешивать это с обычной search quota
 * Spam на failed retry: Cooldown
 * указать это в legal pages + about us + premium

---

## 🧩 UI / Templates

### dealer-card

- [x] добавить AI summary блок
- [x] показывать только если `ai_status = done`

### Отображать

- [x] positives (pros)
- [x] negatives (cons)
- [x] languages (если есть)

### Warning

- [ ] если `reviews_sample_count << reviews_total_count_at_sync` → показывать "Summary based on a limited sample of recent reviews" — **не реализовано**

### UX

- [x] UI не делает акцент на AI
- [x] выглядит как "review insights"
- [x] компактный блок

---

## 📄 Detail Page

- [x] AI summary доступен через `/dealer/<place_id>/ai-summary/` (JSON endpoint)

---

## ⚖️ Юридическое

- [x] AI Disclaimer — присутствует в UI (`ai-summary-disclaimer`)
- [ ] AI Disclaimer в `/agb`
- [ ] проверить необходимость в `/datenschutz`
- [x] disclaimer под AI-блоком

---

## 🚀 Future

- [ ] dealer detail page (full)
- [ ] periodic re-sync (раз в 30 дней)
- [ ] расширение JSON (confidence, tags)

---

## 🧠 Key Design Principle

Deterministic search + async cached AI enrichment

> Persistent cache в БД реализован через `DealerAiSummary`.




