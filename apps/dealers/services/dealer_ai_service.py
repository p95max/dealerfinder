import hashlib
import json
import logging

from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from apps.dealers.models import Dealer, DealerAiSummary
from apps.dealers.services.google_places import get_place_details
from integrations.ai_client import generate_dealer_summary, AiClientError

logger = logging.getLogger(__name__)


def ensure_ai_summary_record(dealer: Dealer) -> DealerAiSummary:
    obj, _ = DealerAiSummary.objects.get_or_create(dealer=dealer)
    return obj


def build_dealer_ai_context(place_details: dict) -> dict:
    reviews = []

    for review in place_details.get("reviews", []):
        if not isinstance(review, dict):
            continue

        text_obj = review.get("text")
        if isinstance(text_obj, dict):
            text = text_obj.get("text")
        else:
            text = None

        if isinstance(text, str) and text.strip():
            reviews.append(text.strip())

    display_name = place_details.get("displayName", {})
    if isinstance(display_name, dict):
        name = display_name.get("text")
    else:
        name = None

    return {
        "name": name,
        "rating": place_details.get("rating"),
        "total_reviews": place_details.get("userRatingCount"),
        "price_level": place_details.get("priceLevel"),
        "opening_hours": place_details.get("regularOpeningHours"),
        "open_now": place_details.get("currentOpeningHours", {}).get("openNow"),
        "website": place_details.get("websiteUri"),
        "phone": place_details.get("nationalPhoneNumber"),
        "types": place_details.get("types", []),
        "reviews": reviews,
    }


def build_source_fingerprint(context: dict) -> str:
    raw = json.dumps(
        {
            "rating": context.get("rating"),
            "total_reviews": context.get("total_reviews"),
            "reviews": context.get("reviews", []),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_summary_up_to_date(summary_obj: DealerAiSummary, fingerprint: str) -> bool:
    return (
        summary_obj.status == DealerAiSummary.STATUS_DONE
        and is_summary_fresh(summary_obj)
        and summary_obj.source_fingerprint == fingerprint
        and summary_obj.prompt_version == settings.AI_PROMPT_VERSION
        and summary_obj.model == settings.AI_MODEL
        and summary_obj.provider == settings.AI_PROVIDER
    )

def is_summary_fresh(summary_obj: DealerAiSummary) -> bool:
    if not summary_obj.generated_at:
        return False

    ttl = timedelta(days=settings.AI_SUMMARY_TTL_DAYS)
    return summary_obj.generated_at >= timezone.now() - ttl


def can_retry_failed_summary(summary_obj: DealerAiSummary) -> bool:
    if summary_obj.status != DealerAiSummary.STATUS_FAILED:
        return False

    cooldown = timedelta(hours=settings.AI_FAILED_RETRY_HOURS)
    return summary_obj.updated_at <= timezone.now() - cooldown


def is_stale_pending_summary(summary_obj: DealerAiSummary) -> bool:
    if summary_obj.status != DealerAiSummary.STATUS_PENDING:
        return False

    stale_after = timedelta(minutes=settings.AI_PENDING_STALE_MINUTES)
    return summary_obj.updated_at <= timezone.now() - stale_after


def validate_ai_result(data: dict) -> dict:
    summary = str(data.get("summary") or "").strip()
    pros = [str(x).strip() for x in (data.get("pros") or []) if str(x).strip()]
    cons = [str(x).strip() for x in (data.get("cons") or []) if str(x).strip()]
    sentiment = str(data.get("sentiment") or "").strip()
    languages = [str(x).strip().lower() for x in (data.get("languages") or []) if str(x).strip()]
    export_friendly = data.get("export_friendly")
    confidence = data.get("confidence")

    if not summary:
        raise ValueError("AI result missing summary")

    if sentiment not in {"positive", "mixed", "negative"}:
        raise ValueError("Invalid sentiment")

    if confidence is not None:
        confidence = float(confidence)
        if confidence < 0 or confidence > 1:
            raise ValueError("Confidence must be between 0 and 1")

    return {
        "summary": summary[:500],
        "pros": pros[:3],
        "cons": cons[:3],
        "sentiment": sentiment,
        "languages": languages[:5],
        "export_friendly": export_friendly if isinstance(export_friendly, bool) or export_friendly is None else None,
        "confidence": confidence,
    }


def generate_ai_summary_for_dealer(dealer: Dealer) -> DealerAiSummary:
    summary_obj = ensure_ai_summary_record(dealer)

    if not settings.AI_ENABLED:
        summary_obj.last_error = "AI is disabled"
        summary_obj.save(update_fields=["last_error", "updated_at"])
        return summary_obj

    details = get_place_details(dealer.google_place_id)
    if not details:
        summary_obj.status = DealerAiSummary.STATUS_FAILED
        summary_obj.summary = ""
        summary_obj.pros = []
        summary_obj.cons = []
        summary_obj.sentiment = ""
        summary_obj.languages = []
        summary_obj.export_friendly = None
        summary_obj.confidence = None
        summary_obj.source_review_count = 0
        summary_obj.raw_response = None
        summary_obj.generated_at = None
        summary_obj.last_error = "No reviews available for AI summary"
        summary_obj.provider = settings.AI_PROVIDER
        summary_obj.model = settings.AI_MODEL
        summary_obj.prompt_version = settings.AI_PROMPT_VERSION
        summary_obj.save(
            update_fields=[
                "status",
                "summary",
                "pros",
                "cons",
                "sentiment",
                "languages",
                "export_friendly",
                "confidence",
                "source_review_count",
                "raw_response",
                "generated_at",
                "last_error",
                "updated_at",
            ]
        )
        return summary_obj

    context = build_dealer_ai_context(details)
    reviews = context.get("reviews", [])
    review_count = len(reviews)

    if review_count == 0:
        logger.info(
            "AI summary skipped because no reviews are available",
            extra={
                "event": "ai_summary_skipped_no_reviews",
                "dealer_id": dealer.pk,
            },
        )
        summary_obj.status = DealerAiSummary.STATUS_FAILED
        summary_obj.summary = ""
        summary_obj.pros = []
        summary_obj.cons = []
        summary_obj.sentiment = ""
        summary_obj.languages = []
        summary_obj.export_friendly = None
        summary_obj.confidence = None
        summary_obj.source_review_count = 0
        summary_obj.raw_response = None
        summary_obj.generated_at = None
        summary_obj.last_error = "No reviews available for AI summary"
        summary_obj.save(
            update_fields=[
                "status",
                "summary",
                "pros",
                "cons",
                "sentiment",
                "languages",
                "export_friendly",
                "confidence",
                "source_review_count",
                "raw_response",
                "generated_at",
                "last_error",
                "updated_at",
            ]
        )
        return summary_obj

    fingerprint = build_source_fingerprint(context)

    if is_summary_up_to_date(summary_obj, fingerprint):
        logger.info(
            "AI summary skipped because it is up to date",
            extra={
                "event": "ai_summary_skipped_cached",
                "dealer_id": dealer.pk,
            },
        )
        return summary_obj

    if (
        summary_obj.status == DealerAiSummary.STATUS_FAILED
        and not can_retry_failed_summary(summary_obj)
    ):
        return summary_obj

    logger.info(
        "AI summary generation requested",
        extra={
            "event": "ai_summary_requested",
            "dealer_id": dealer.pk,
            "review_count": review_count,
        },
    )

    summary_obj.status = DealerAiSummary.STATUS_PENDING
    summary_obj.last_error = ""
    summary_obj.provider = settings.AI_PROVIDER
    summary_obj.model = settings.AI_MODEL
    summary_obj.prompt_version = settings.AI_PROMPT_VERSION
    summary_obj.save(
        update_fields=[
            "status",
            "last_error",
            "provider",
            "model",
            "prompt_version",
            "updated_at",
        ]
    )

    try:
        logger.info("AI CALL STARTED", extra={"dealer_id": dealer.pk})
        result = generate_dealer_summary(context)
        validated = validate_ai_result(result)
    except (AiClientError, ValueError, TypeError) as exc:
        logger.exception(
            "AI summary generation failed",
            extra={
                "event": "ai_summary_failed",
                "dealer_id": dealer.pk,
            },
        )
        summary_obj.status = DealerAiSummary.STATUS_FAILED
        summary_obj.provider = settings.AI_PROVIDER
        summary_obj.model = settings.AI_MODEL
        summary_obj.prompt_version = settings.AI_PROMPT_VERSION
        summary_obj.summary = ""
        summary_obj.pros = []
        summary_obj.cons = []
        summary_obj.sentiment = ""
        summary_obj.languages = []
        summary_obj.export_friendly = None
        summary_obj.confidence = None
        summary_obj.raw_response = None
        summary_obj.generated_at = None
        summary_obj.last_error = str(exc)[:1000]
        summary_obj.source_review_count = review_count
        summary_obj.source_fingerprint = fingerprint
        summary_obj.save(
            update_fields=[
                "status",
                "provider",
                "model",
                "prompt_version",
                "summary",
                "pros",
                "cons",
                "sentiment",
                "languages",
                "export_friendly",
                "confidence",
                "raw_response",
                "generated_at",
                "last_error",
                "updated_at",
            ]
        )
        return summary_obj

    summary_obj.status = DealerAiSummary.STATUS_DONE
    summary_obj.provider = settings.AI_PROVIDER
    summary_obj.model = settings.AI_MODEL
    summary_obj.prompt_version = settings.AI_PROMPT_VERSION
    summary_obj.summary = validated["summary"]
    summary_obj.pros = validated["pros"]
    summary_obj.cons = validated["cons"]
    summary_obj.sentiment = validated["sentiment"]
    summary_obj.languages = validated["languages"]
    summary_obj.export_friendly = validated["export_friendly"]
    summary_obj.confidence = validated["confidence"]
    summary_obj.source_review_count = review_count
    summary_obj.source_fingerprint = fingerprint
    summary_obj.raw_response = result
    summary_obj.last_error = ""
    summary_obj.generated_at = timezone.now()
    summary_obj.save()

    logger.info(
        "AI summary generated successfully",
        extra={
            "event": "ai_summary_generated",
            "dealer_id": dealer.pk,
            "review_count": review_count,
        },
    )

    return summary_obj