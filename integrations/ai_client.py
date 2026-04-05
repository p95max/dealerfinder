import json
import logging
from typing import Any

from django.conf import settings
from openai import OpenAI

from common.exceptions import AiClientError

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.AI_API_KEY)


def _safe_parse_json(text: str) -> dict:
    text = text.strip()

    if text.startswith("```"):
        text = text.split("```")[1]

    return json.loads(text)


def _generate_with_openai(dealer_context: dict[str, Any]) -> dict[str, Any]:
    reviews = dealer_context.get("reviews", [])

    if not reviews:
        raise AiClientError("No reviews provided for AI analysis")

    prompt = f"""
You are analyzing customer reviews of a car dealer.

Based ONLY on the reviews below, generate JSON.

Rules:
- Do NOT invent facts
- If insufficient data → return null fields
- Max 300 chars summary
- Max 3 pros / cons
- Be conservative in conclusions

Return ONLY JSON:

{{
  "summary": "...",
  "pros": [...],
  "cons": [...],
  "sentiment": "positive | mixed | negative",
  "languages": [...],
  "export_friendly": true | false | null,
  "confidence": 0.0-1.0
}}

Reviews:
{json.dumps(reviews, ensure_ascii=False)}
"""

    try:
        response = client.chat.completions.create(
            model=settings.AI_MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": "You output strict JSON only."},
                {"role": "user", "content": prompt},
            ],
        )

        content = response.choices[0].message.content

        data = _safe_parse_json(content)

        logger.info(
            "AI response received",
            extra={
                "event": "ai_response_received",
                "review_count": len(reviews),
            },
        )

        return data

    except Exception as exc:
        logger.exception(
            "OpenAI request failed",
            extra={
                "event": "ai_request_failed",
            },
        )
        raise AiClientError(str(exc))


