from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from openai import OpenAI

from common.exceptions import AiClientError
from apps.dealers.ai.prompts import build_dealer_summary_prompt
from apps.dealers.ai.parsers import safe_parse_json

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.AI_API_KEY)


def _generate_with_openai(prompt: str) -> dict[str, Any]:
    """
    Send a prompt to OpenAI and parse raw JSON response.
    This layer is transport-only and contains no dealer business logic.
    """
    try:
        response = client.chat.completions.create(
            model=settings.AI_MODEL,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a structured data extraction assistant. "
                        "Return JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            timeout=settings.AI_REQUEST_TIMEOUT,
        )
    except Exception as exc:
        logger.exception(
            "OpenAI request failed",
            extra={"event": "openai_request_failed"},
        )
        raise AiClientError(f"OpenAI request failed: {exc}") from exc

    try:
        content = response.choices[0].message.content or ""
    except (AttributeError, IndexError, TypeError) as exc:
        raise AiClientError("OpenAI response has unexpected format") from exc

    return safe_parse_json(content)


def generate_dealer_summary(dealer_context: dict[str, Any]) -> dict[str, Any]:
    """
    Build prompt for dealer summary generation and return parsed raw JSON.
    Validation of domain schema stays outside this integration layer.
    """
    reviews = dealer_context.get("reviews", [])
    if not reviews:
        raise AiClientError("No dealer reviews available for AI analysis")

    prompt = build_dealer_summary_prompt(dealer_context)
    return _generate_with_openai(prompt)