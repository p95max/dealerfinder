import hashlib
import json
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.dealers.models import Dealer, DealerAiSummary
from apps.dealers.ai.quotas import (
    get_anonymous_ai_quota_status_by_ip,
    consume_anonymous_ai_quota_by_ip,
)
from apps.dealers.ai.system_quota import (
    consume_ai_system_quota,
    get_ai_system_quota_status,
)
from apps.dealers.ai.cache import (
    delete_cached_ai_summary_payload,
    set_cached_ai_summary_payload,
)
from apps.dealers.ai.locks import (
    acquire_ai_summary_lock,
    release_ai_summary_lock,
)
from apps.dealers.services.google_places import get_place_details
from apps.users.services.ai_quota_service import (
    consume_authenticated_ai_quota,
    get_authenticated_ai_quota_status,
)
from common.services.feature_flags import is_feature_enabled
from integrations.ai_client import AiClientError, generate_dealer_summary
from apps.dealers.ai.parsers import validate_dealer_summary_result

logger = logging.getLogger(__name__)

NON_RETRYABLE_ERROR_CODES = {
    "ai_disabled",
    "quota_exceeded_anon",
    "quota_exceeded_authenticated",
    "quota_exceeded_premium",
    "system_quota_exceeded",
}


# =========================
# CORE
# =========================
def generate_ai_summary_for_dealer(
    dealer: Dealer,
    *,
    user=None,
    client_ip=None,
) -> DealerAiSummary:
    summary_obj = ensure_ai_summary_record(dealer)

    if not is_ai_summary_feature_enabled():
        delete_cached_ai_summary_payload(dealer.google_place_id)
        summary_obj.status = DealerAiSummary.STATUS_FAILED
        summary_obj.last_error = "ai_disabled"
        summary_obj.save(update_fields=["status", "last_error", "updated_at"])
        return summary_obj

    lock = acquire_ai_summary_lock(
        dealer.google_place_id,
        ttl_seconds=settings.AI_DEDUP_LOCK_TTL_SECONDS,
    )

    if not lock:
        logger.info(
            "AI summary generation skipped because lock is already held",
            extra={
                "event": "ai_summary_dedup_lock_skipped",
                "dealer_id": dealer.pk,
                "place_id": dealer.google_place_id,
            },
        )
        return summary_obj

    try:
        details = get_place_details(dealer.google_place_id)

        if not details:
            delete_cached_ai_summary_payload(dealer.google_place_id)
            return _mark_summary_failed_no_reviews(
                summary_obj,
                error_message="No reviews available for AI summary",
                review_count=0,
                reviews_total_count=0,
            )

        data = prepare_ai_generation_data(details)

        if data["review_count"] == 0:
            logger.info(
                "AI summary skipped because no reviews are available",
                extra={
                    "event": "ai_summary_skipped_no_reviews",
                    "dealer_id": dealer.pk,
                },
            )
            delete_cached_ai_summary_payload(dealer.google_place_id)
            return _mark_summary_failed_no_reviews(
                summary_obj,
                error_message="No reviews available for AI summary",
                review_count=0,
                reviews_total_count=data["reviews_total_count"],
                fingerprint=data["fingerprint"],
            )

        if is_summary_up_to_date(
            summary_obj,
            data["fingerprint"],
            data["reviews_total_count"],
        ):
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
                "review_count": data["review_count"],
            },
        )

        delete_cached_ai_summary_payload(dealer.google_place_id)
        mark_summary_pending(summary_obj)

        quota_allowed, quota_error = check_and_consume_ai_quota(
            user=user,
            client_ip=client_ip,
        )
        if not quota_allowed:
            delete_cached_ai_summary_payload(dealer.google_place_id)
            summary_obj.status = DealerAiSummary.STATUS_FAILED
            summary_obj.last_error = quota_error
            summary_obj.save(
                update_fields=[
                    "status",
                    "last_error",
                    "updated_at",
                ]
            )
            return summary_obj

        try:
            logger.info(
                "AI CALL STARTED",
                extra={
                    "event": "ai_call_started",
                    "dealer_id": dealer.pk,
                },
            )
            raw_result = generate_dealer_summary(data["context"])
            validated = validate_dealer_summary_result(raw_result)
        except (AiClientError, ValueError, TypeError) as exc:
            delete_cached_ai_summary_payload(dealer.google_place_id)
            logger.exception(
                "AI summary generation failed",
                extra={
                    "event": "ai_summary_failed",
                    "dealer_id": dealer.pk,
                },
            )
            return apply_ai_failure(
                summary_obj,
                exc=exc,
                review_count=data["review_count"],
                reviews_total_count=data["reviews_total_count"],
                is_limited_sample=data["is_limited_sample"],
                fingerprint=data["fingerprint"],
            )

        delete_cached_ai_summary_payload(dealer.google_place_id)
        return apply_ai_success(
            summary_obj,
            validated=validated,
            raw_result=raw_result,
            review_count=data["review_count"],
            reviews_total_count=data["reviews_total_count"],
            is_limited_sample=data["is_limited_sample"],
            fingerprint=data["fingerprint"],
        )

    finally:
        release_ai_summary_lock(lock)


# =========================
# DECISION HELPERS
# =========================
def is_ai_summary_feature_enabled() -> bool:
    return settings.AI_ENABLED and is_feature_enabled(
        "ai_summary_enabled",
        default=settings.FEATURE_AI_SUMMARY_ENABLED,
    )


def is_summary_up_to_date(
    summary_obj: DealerAiSummary,
    fingerprint: str,
    reviews_total_count: int,
) -> bool:
    return (
        summary_obj.status == DealerAiSummary.STATUS_DONE
        and is_summary_fresh(summary_obj)
        and summary_obj.source_fingerprint == fingerprint
        and summary_obj.reviews_total_count_at_sync == reviews_total_count
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

    if summary_obj.last_error in NON_RETRYABLE_ERROR_CODES:
        return False

    cooldown = timedelta(hours=settings.AI_FAILED_RETRY_HOURS)
    return summary_obj.updated_at <= timezone.now() - cooldown


def is_stale_pending_summary(summary_obj: DealerAiSummary) -> bool:
    if summary_obj.status != DealerAiSummary.STATUS_PENDING:
        return False

    stale_after = timedelta(minutes=settings.AI_PENDING_STALE_MINUTES)
    return summary_obj.updated_at <= timezone.now() - stale_after


# =========================
# HELPERS
# =========================
def ensure_ai_summary_record(dealer: Dealer) -> DealerAiSummary:
    obj, _ = DealerAiSummary.objects.get_or_create(dealer=dealer)
    return obj


def prepare_ai_generation_data(details: dict) -> dict:
    context = build_dealer_ai_context(details)
    reviews = context.get("reviews", [])
    review_count = len(reviews)
    reviews_total_count = int(context.get("total_reviews") or 0)

    return {
        "context": context,
        "review_count": review_count,
        "reviews_total_count": reviews_total_count,
        "is_limited_sample": (
            review_count < settings.AI_MIN_REVIEWS_FOR_RELIABLE_SUMMARY
        ),
        "fingerprint": build_source_fingerprint(context),
    }


def check_and_consume_ai_quota(*, user=None, client_ip=None) -> tuple[bool, str | None]:
    if user and user.is_authenticated:
        quota = get_authenticated_ai_quota_status(user)
        if not quota.allowed:
            return False, _get_authenticated_quota_error_code(user)

        consume_authenticated_ai_quota(user)
        return True, None

    if client_ip is not None:
        quota = get_anonymous_ai_quota_status_by_ip(client_ip)
        if not quota.allowed:
            return False, "quota_exceeded_anon"

        system_quota = get_ai_system_quota_status()
        if not system_quota.allowed:
            return False, "system_quota_exceeded"

        consume_anonymous_ai_quota_by_ip(client_ip)
        consume_ai_system_quota()
        return True, None

    return True, None


def mark_summary_pending(summary_obj: DealerAiSummary) -> None:
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


def apply_ai_failure(
    summary_obj: DealerAiSummary,
    *,
    exc: Exception,
    review_count: int,
    reviews_total_count: int,
    is_limited_sample: bool,
    fingerprint: str,
) -> DealerAiSummary:
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
    summary_obj.reviews_total_count_at_sync = reviews_total_count
    summary_obj.is_limited_sample = is_limited_sample
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
            "source_review_count",
            "reviews_total_count_at_sync",
            "is_limited_sample",
            "source_fingerprint",
            "updated_at",
        ]
    )
    return summary_obj


def apply_ai_success(
    summary_obj: DealerAiSummary,
    *,
    validated: dict,
    raw_result: dict,
    review_count: int,
    reviews_total_count: int,
    is_limited_sample: bool,
    fingerprint: str,
) -> DealerAiSummary:
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
    summary_obj.reviews_total_count_at_sync = reviews_total_count
    summary_obj.is_limited_sample = is_limited_sample
    summary_obj.source_fingerprint = fingerprint
    summary_obj.raw_response = raw_result
    summary_obj.last_error = ""
    summary_obj.generated_at = timezone.now()
    summary_obj.save()

    payload = {
        "status": "done",
        "summary": summary_obj.summary or "",
        "pros": summary_obj.pros or [],
        "cons": summary_obj.cons or [],
    }

    set_cached_ai_summary_payload(
        summary_obj.dealer.google_place_id,
        payload,
    )
    
    return summary_obj


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



def _get_authenticated_quota_error_code(user) -> str:
    if getattr(user, "plan", "") == "premium":
        return "quota_exceeded_premium"
    return "quota_exceeded_authenticated"


def _mark_summary_failed_no_reviews(
    summary_obj: DealerAiSummary,
    *,
    error_message: str,
    review_count: int = 0,
    reviews_total_count: int = 0,
    fingerprint: str = "",
) -> DealerAiSummary:
    summary_obj.status = DealerAiSummary.STATUS_FAILED
    summary_obj.summary = ""
    summary_obj.pros = []
    summary_obj.cons = []
    summary_obj.sentiment = ""
    summary_obj.languages = []
    summary_obj.export_friendly = None
    summary_obj.confidence = None
    summary_obj.source_review_count = review_count
    summary_obj.reviews_total_count_at_sync = reviews_total_count
    summary_obj.source_fingerprint = fingerprint
    summary_obj.raw_response = None
    summary_obj.generated_at = None
    summary_obj.is_limited_sample = True
    summary_obj.last_error = error_message
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
            "reviews_total_count_at_sync",
            "is_limited_sample",
            "source_fingerprint",
            "raw_response",
            "generated_at",
            "last_error",
            "provider",
            "model",
            "prompt_version",
            "updated_at",
        ]
    )
    return summary_obj