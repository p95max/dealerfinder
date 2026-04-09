import json
import logging

from django.conf import settings

from apps.dealers.models import Dealer, DealerAiSummary
from apps.dealers.services.dealer_ai_cache_service import (
    get_cached_ai_summary_payload,
    set_cached_ai_summary_payload,
)
from apps.dealers.services.dealer_ai_service import (
    generate_ai_summary_for_dealer,
    is_summary_fresh,
)
from apps.dealers.services.ai_rate_limit_service import AiRateLimitService, RateLimitExceeded
from apps.dealers.services.dealer_ai_cache_service import delete_cached_ai_summary_payload

logger = logging.getLogger(__name__)


def build_ai_summary_payload(ai: DealerAiSummary | None) -> dict:
    if not ai:
        return {
            "status": "pending",
            "summary": "",
            "pros": [],
            "cons": [],
            "error_code": "not_generated_yet",
        }

    if ai.status == DealerAiSummary.STATUS_DONE and is_summary_fresh(ai):
        return {
            "status": ai.status,
            "summary": ai.summary or "",
            "pros": ai.pros or [],
            "cons": ai.cons or [],
        }

    if ai.status == DealerAiSummary.STATUS_PENDING:
        return {
            "status": ai.status,
            "summary": "",
            "pros": [],
            "cons": [],
        }

    if ai.status == DealerAiSummary.STATUS_FAILED:
        error_code = ai.last_error or "ai_unavailable"
        message = "AI summary unavailable"

        if error_code == "system_quota_exceeded":
            message = (
                "AI summaries are temporarily unavailable due to today's system limit.\n"
                "Please try again tomorrow."
            )
        elif error_code == "quota_exceeded_anon":
            message = (
                f"Guest limit reached: {settings.ANON_AI_DAILY_LIMIT} AI summaries per day.\n"
                f"Sign in to get {settings.FREE_AI_DAILY_LIMIT} summaries per day."
            )
        elif error_code == "quota_exceeded_free":
            message = (
                f"Free plan limit reached: {settings.FREE_AI_DAILY_LIMIT} AI summaries per day.\n"
                f"Upgrade to Premium ({settings.PREMIUM_AI_DAILY_LIMIT} sum./day) for more daily AI summaries."
            )

        return {
            "status": "failed",
            "summary": "",
            "pros": [],
            "cons": [],
            "error_code": error_code,
            "message": message,
        }

    return {
        "status": "pending",
        "summary": "",
        "pros": [],
        "cons": [],
    }


def attach_ai_summaries_to_dealers(dealers: list[dict]) -> list[dict]:
    place_ids = [
        dealer.get("place_id")
        for dealer in dealers
        if dealer.get("place_id")
    ]

    if not place_ids:
        return dealers

    ai_summary_map = {
        item.dealer.google_place_id: item
        for item in DealerAiSummary.objects.select_related("dealer").filter(
            dealer__google_place_id__in=place_ids
        )
    }

    for dealer in dealers:
        payload = build_ai_summary_payload(ai_summary_map.get(dealer.get("place_id")))
        dealer["ai_summary"] = payload
        dealer["ai_summary_pros_json"] = json.dumps(payload["pros"], ensure_ascii=False)
        dealer["ai_summary_cons_json"] = json.dumps(payload["cons"], ensure_ascii=False)

    logger.info(
        "AI summaries attached to dealer list",
        extra={
            "event": "ai_summaries_attached",
            "place_ids_count": len(place_ids),
            "ai_summary_map_count": len(ai_summary_map),
            "place_ids": place_ids[:5],
        },
    )

    return dealers


def get_dealer_ai_summary_payload(place_id: str, request=None) -> tuple[dict, int]:
    try:
        dealer = Dealer.objects.get(google_place_id=place_id)
    except Dealer.DoesNotExist:
        return (
            {"status": "not_found", "summary": "", "pros": [], "cons": []},
            404,
        )

    cached_payload = get_cached_ai_summary_payload(place_id)
    if cached_payload:
        logger.info(
            "AI summary payload served from Redis cache",
            extra={
                "event": "ai_summary_cache_hit",
                "place_id": place_id,
            },
        )

        return cached_payload, 200

    else:
        logger.info(
            "AI summary payload Redis cache miss",
            extra={
                "event": "ai_summary_cache_miss",
                "place_id": place_id,
            },
        )

    ai = getattr(dealer, "ai_summary", None)

    if ai and ai.status == DealerAiSummary.STATUS_DONE and is_summary_fresh(ai):
        payload = build_ai_summary_payload(ai)
        set_cached_ai_summary_payload(place_id, payload)
        return payload, 200

    if ai and ai.status == DealerAiSummary.STATUS_FAILED:
        payload = build_ai_summary_payload(ai)
        set_cached_ai_summary_payload(place_id, payload)
        return payload, 200

    if request:
        try:
            AiRateLimitService().check(request.user, request)
        except RateLimitExceeded:
            return (
                {
                    "status": "failed",
                    "summary": "",
                    "pros": [],
                    "cons": [],
                    "error_code": "rate_limited",
                    "message": "Too many requests. Please slow down.",
                },
                429,
            )

    try:
        ai = generate_ai_summary_for_dealer(
            dealer,
            user=request.user if request and request.user.is_authenticated else None,
            request=request,
        )
    except Exception:
        delete_cached_ai_summary_payload(place_id)
        logger.exception("AI generation failed")

        return (
            {
                "status": "failed",
                "summary": "",
                "pros": [],
                "cons": [],
                "error_code": "ai_error",
                "message": "AI service temporarily unavailable.",
            },
            200,
        )

    payload = build_ai_summary_payload(ai)
    set_cached_ai_summary_payload(place_id, payload)
    return payload, 200


def generate_dealer_ai_summary_payload(place_id: str, *, request=None) -> tuple[dict, int]:
    try:
        dealer = Dealer.objects.get(google_place_id=place_id)
    except Dealer.DoesNotExist:
        return (
            {"status": "not_found", "summary": "", "pros": [], "cons": []},
            404,
        )

    if request:
        try:
            AiRateLimitService().check(request.user, request)
        except RateLimitExceeded:
            return (
                {
                    "status": "failed",
                    "summary": "",
                    "pros": [],
                    "cons": [],
                    "error_code": "rate_limited",
                    "message": "Too many requests. Please slow down.",
                },
                429,
            )

    try:
        ai = generate_ai_summary_for_dealer(
            dealer,
            user=request.user if request and request.user.is_authenticated else None,
            request=request,
        )
    except Exception:
        delete_cached_ai_summary_payload(place_id)
        logger.exception("AI generation failed")
        return (
            {
                "status": "failed",
                "summary": "",
                "pros": [],
                "cons": [],
                "error_code": "ai_error",
                "message": "AI service temporarily unavailable.",
            },
            200,
        )

    payload = build_ai_summary_payload(ai)
    set_cached_ai_summary_payload(place_id, payload)
    return payload, 200