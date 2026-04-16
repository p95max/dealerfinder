from __future__ import annotations

import json
import re
from typing import Any

from common.exceptions import AiClientError


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

        if confidence < 0 or confidence > 1:
            raise AiClientError("AI result confidence must be between 0 and 1")

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