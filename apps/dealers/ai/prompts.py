from __future__ import annotations



def build_dealer_summary_prompt(dealer_context: dict) -> str:
    reviews = dealer_context.get("reviews", [])

    return f"""
You are analyzing customer reviews of a car dealer.

Based ONLY on the reviews below, generate a JSON object.

Rules:
- Do NOT invent facts
- If insufficient data → return null fields
- Max 300 chars summary
- Max 3 pros
- Max 3 cons
- Be conservative in conclusions
- Output MUST be valid JSON

Schema:
{{
  "summary": "string | null",
  "pros": ["string"],
  "cons": ["string"],
  "sentiment": "positive|mixed|negative|null",
  "languages": ["string"],
  "export_friendly": true|false|null,
  "confidence": number|null
}}

Constraints:
- confidence: 0 ≤ value ≤ 1
- languages: lowercase (e.g. "german", "english")
- No text outside JSON

Reviews:
{reviews}
""".strip()