from __future__ import annotations

import json
import re
import logging

from typing import Any

from common.exceptions import AiClientError

logger = logging.getLogger(__name__)


def safe_parse_json(text: str) -> dict[str, Any]:
    """
    Parse JSON response safely, including fenced markdown payloads.
    """
    if not isinstance(text, str) or not text.strip():
        raise AiClientError("AI response is empty")

    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", cleaned)
        cleaned = cleaned.rstrip("` \n")

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AiClientError(f"AI response is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise AiClientError("AI response must be a JSON object")

    return data


def validate_dealer_summary_result(data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate and normalize AI result payload for dealer summary domain.
    """
    summary = str(data.get("summary") or "").strip()
    pros = [str(x).strip() for x in (data.get("pros") or []) if str(x).strip()]
    cons = [str(x).strip() for x in (data.get("cons") or []) if str(x).strip()]
    sentiment = str(data.get("sentiment") or "").strip()
    languages = [
        str(x).strip().lower()
        for x in (data.get("languages") or [])
        if str(x).strip()
    ]
    export_friendly = data.get("export_friendly")
    confidence = data.get("confidence")

    if not summary:
        raise AiClientError("AI result missing summary")

    if sentiment not in {"positive", "mixed", "negative"}:
        raise AiClientError("AI result has invalid sentiment")

    if confidence is not None:
        try:
            confidence = float(confidence)
        except (TypeError, ValueError) as exc:
            raise AiClientError("AI result has invalid confidence") from exc

        original_confidence = confidence
        confidence = max(0.0, min(1.0, confidence))

        if confidence != original_confidence:
            logger.warning(
                "AI confidence was clamped",
                extra={
                    "event": "ai_confidence_clamped",
                    "original_confidence": original_confidence,
                    "clamped_confidence": confidence,
                },
            )

    return {
        "summary": summary[:500],
        "pros": pros[:3],
        "cons": cons[:3],
        "sentiment": sentiment,
        "languages": languages[:5],
        "export_friendly": (
            export_friendly
            if isinstance(export_friendly, bool) or export_friendly is None
            else None
        ),
        "confidence": confidence,
    }


def safe_validate_or_fallback(data: dict) -> dict:
    try:
        return validate_dealer_summary_result(data)
    except Exception:
        return {
            "summary": None,
            "pros": [],
            "cons": [],
            "sentiment": None,
            "languages": [],
            "export_friendly": None,
            "confidence": None,
        }