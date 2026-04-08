import json
import logging

from django.conf import settings

from apps.dealers.models import Dealer, DealerAiSummary
from apps.dealers.services.dealer_ai_service import (
    generate_ai_summary_for_dealer,
    is_summary_fresh,
)

logger = logging.getLogger(__name__)


def build_ai_summary_payload(ai: DealerAiSummary | None) -> dict:
    if not ai:
        return {
            "status": "pending",
            "summary": "",
            "pros": [],
            "cons": [],
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
        return {
            "status": ai.status,
            "summary": "",
            "pros": [],
            "cons": [],
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


def get_dealer_ai_summary_payload(place_id: str) -> tuple[dict, int]:
    try:
        dealer = Dealer.objects.get(google_place_id=place_id)
    except Dealer.DoesNotExist:
        return (
            {"status": "not_found", "summary": "", "pros": [], "cons": []},
            404,
        )

    ai = getattr(dealer, "ai_summary", None)

    if ai is None:
        return (
            {"status": "pending", "summary": "", "pros": [], "cons": []},
            200,
        )

    if ai.status == DealerAiSummary.STATUS_DONE and is_summary_fresh(ai):
        return build_ai_summary_payload(ai), 200

    if ai.status == DealerAiSummary.STATUS_FAILED:
        return (
            {"status": "failed", "summary": "", "pros": [], "cons": []},
            200,
        )

    return (
        {"status": "pending", "summary": "", "pros": [], "cons": []},
        200,
    )


def generate_dealer_ai_summary_payload(place_id: str, *, request=None) -> tuple[dict, int]:
    try:
        dealer = Dealer.objects.get(google_place_id=place_id)
    except Dealer.DoesNotExist:
        return (
            {"status": "not_found", "summary": "", "pros": [], "cons": []},
            404,
        )

    ai = generate_ai_summary_for_dealer(
        dealer,
        user=request.user if request and request.user.is_authenticated else None,
        request=request,
    )

    return build_ai_summary_payload(ai), 200