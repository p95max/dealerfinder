import logging

from django.conf import settings

from apps.dealers.models import Dealer, DealerAiSummary
from apps.dealers.services.dealer_ai_service import (
    can_retry_failed_summary,
    is_stale_pending_summary,
    is_summary_fresh,
)

logger = logging.getLogger(__name__)


def enqueue_ai_summaries_for_dealers(place_ids: list[str], limit: int | None = None) -> int:
    """
    Create/update pending AI summary jobs for top-N dealers.
    """
    if not settings.AI_ENABLED:
        return 0

    if not place_ids:
        return 0

    effective_limit = limit or settings.AI_SYNC_LIMIT
    if effective_limit <= 0:
        return 0

    dealers = list(
        Dealer.objects.filter(google_place_id__in=place_ids)[:effective_limit]
    )

    enqueued = 0

    for dealer in dealers:
        summary, created = DealerAiSummary.objects.get_or_create(
            dealer=dealer,
            defaults={
                "status": DealerAiSummary.STATUS_PENDING,
                "provider": settings.AI_PROVIDER,
                "model": settings.AI_MODEL,
                "prompt_version": settings.AI_PROMPT_VERSION,
                "last_error": "",
            },
        )

        if created:
            enqueued += 1
            continue

        should_enqueue = False

        if summary.status == DealerAiSummary.STATUS_DONE and not is_summary_fresh(summary):
            should_enqueue = True
        elif summary.status == DealerAiSummary.STATUS_FAILED and can_retry_failed_summary(summary):
            should_enqueue = True
        elif summary.status == DealerAiSummary.STATUS_PENDING and is_stale_pending_summary(summary):
            should_enqueue = True

        if not should_enqueue:
            continue

        summary.status = DealerAiSummary.STATUS_PENDING
        summary.provider = settings.AI_PROVIDER
        summary.model = settings.AI_MODEL
        summary.prompt_version = settings.AI_PROMPT_VERSION
        summary.last_error = ""
        summary.save(
            update_fields=[
                "status",
                "provider",
                "model",
                "prompt_version",
                "last_error",
                "updated_at",
            ]
        )
        enqueued += 1

    logger.info(
        "AI summaries enqueued from search flow",
        extra={
            "event": "ai_summaries_enqueued",
            "requested_count": len(place_ids),
            "limit": effective_limit,
            "enqueued_count": enqueued,
        },
    )

    return enqueued