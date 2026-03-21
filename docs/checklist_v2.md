# DealerFinder — v2 Checklist (AI Integration)

## Модели
- [ ] `Dealer`: добавить поля `ai_summary` (JSONField, nullable), `ai_synced_at` (DateTimeField, nullable)

## Google Places — Place Details
- [ ] `integrations/google_places.py` — добавить `get_place_details(place_id)`
- [ ] FieldMask для details: `reviews`, `rating`, `userRatingCount`, `priceLevel`, `regularOpeningHours`, `currentOpeningHours`, `websiteUri`, `nationalPhoneNumber`, `types`

## AI Service
- [ ] `apps/dealers/services/ai_service.py` — сборка `dealer_context` из Place Details
- [ ] Промпт для Claude Haiku — структурированный JSON на выходе:
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
- [ ] Вызов `claude-haiku-4-5` через Anthropic API
- [ ] Парсинг и валидация JSON-ответа
- [ ] Если отзывов нет — AI не вызывается, `ai_summary = None`

## Cache & Flow
- [ ] AI вызывается **один раз на дилера** (cache MISS по `ai_synced_at`)
- [ ] Результат сохраняется в `Dealer.ai_summary`
- [ ] Повторные запросы — только из БД, без вызова API

## Интеграция в search flow
- [ ] После нормализации результатов — для каждого нового дилера триггерить AI enrichment
- [ ] Eager loading: `ai_summary` возвращается вместе с результатами поиска (не lazy)

## Шаблоны
- [ ] `dealer-card` — добавить блок AI summary (показывается только если `ai_summary` не None)
- [ ] Отобразить: positives, negatives, languages (если есть)
- [ ] UI не раскрывает что это AI — просто компактный info-блок

## Юридическое
- [ ] AI Disclaimer в `/agb` и `/datenschutz`
- [ ] Disclaimer под AI-блоком на карточке дилера (мелкий текст)