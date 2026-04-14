import logging
from datetime import timedelta

from django.conf import settings
from django.utils.timezone import now

from apps.dealers.models import Dealer, DealerAiSummary
from apps.dealers.tasks import generate_dealer_ai_summary_task
from apps.dealers.ai.service import (
    can_retry_failed_summary,
    is_stale_pending_summary,
    is_summary_fresh,
)

from django_redis import get_redis_connection

logger = logging.getLogger(__name__)
redis_client = get_redis_connection("default")


def enqueue_ai_summaries_for_dealers(
    place_ids: list[str],
    limit: int | None = None,
    *,
    user_id: int | None = None,
    client_ip: str | None = None,
    force: bool = False,
) -> int:
    """
    Safer enqueue:
    - stable ordering
    - Redis dedup (anti-spam)
    - less aggressive retry
    """

    if not settings.AI_ENABLED:
        return 0

    if not place_ids:
        return 0

    effective_limit = limit or settings.AI_SYNC_LIMIT
    if effective_limit <= 0:
        return 0

    dealers = list(
        Dealer.objects
        .filter(google_place_id__in=place_ids)
        .order_by("id")[:effective_limit]
    )

    enqueued = 0

    for dealer in dealers:
        place_id = dealer.google_place_id

        lock_key = f"ai:lock:{place_id}"
        if redis_client.get(lock_key):
            logger.info(
                "AI enqueue skipped (dedup)",
                extra={"event": "ai_enqueue_skipped_dedup", "place_id": place_id},
            )
            continue

        redis_client.setex(lock_key, 60, 1)

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

        if force:
            if summary.status != DealerAiSummary.STATUS_PENDING:
                summary.status = DealerAiSummary.STATUS_PENDING
                summary.provider = settings.AI_PROVIDER
                summary.model = settings.AI_MODEL
                summary.prompt_version = settings.AI_PROMPT_VERSION
                summary.last_error = ""
                summary.save(update_fields=[
                    "status",
                    "provider",
                    "model",
                    "prompt_version",
                    "last_error",
                    "updated_at",
                ])

            result = generate_dealer_ai_summary_task.delay(
                place_id=place_id,
                user_id=user_id,
                client_ip=client_ip,
            )

            logger.info(
                "AI summary task dispatched (forced)",
                extra={
                    "event": "ai_summary_task_dispatched",
                    "place_id": place_id,
                    "task_id": result.id,
                    "force": True,
                },
            )

            enqueued += 1
            continue

        if created:
            result = generate_dealer_ai_summary_task.delay(
                place_id=place_id,
                user_id=user_id,
                client_ip=client_ip,
            )

            logger.info(
                "AI summary task dispatched (created)",
                extra={
                    "event": "ai_summary_task_dispatched",
                    "place_id": place_id,
                    "task_id": result.id,
                    "force": False,
                },
            )

            enqueued += 1
            continue

        # =========================
        # RETRY / STALE LOGIC
        # =========================
        should_enqueue = False

        if (
            summary.status == DealerAiSummary.STATUS_DONE
            and not is_summary_fresh(summary)
            and summary.updated_at < now() - timedelta(hours=6)
        ):
            should_enqueue = True

        elif (
            summary.status == DealerAiSummary.STATUS_FAILED
            and can_retry_failed_summary(summary)
        ):
            should_enqueue = True

        elif (
            summary.status == DealerAiSummary.STATUS_PENDING
            and is_stale_pending_summary(summary)
        ):
            should_enqueue = True

        if not should_enqueue:
            continue

        summary.status = DealerAiSummary.STATUS_PENDING
        summary.provider = settings.AI_PROVIDER
        summary.model = settings.AI_MODEL
        summary.prompt_version = settings.AI_PROMPT_VERSION
        summary.last_error = ""

        summary.save(update_fields=[
            "status",
            "provider",
            "model",
            "prompt_version",
            "last_error",
            "updated_at",
        ])

        result = generate_dealer_ai_summary_task.delay(
            place_id=place_id,
            user_id=user_id,
            client_ip=client_ip,
        )

        logger.info(
            "AI summary task dispatched (retry/stale)",
            extra={
                "event": "ai_summary_task_dispatched",
                "place_id": place_id,
                "task_id": result.id,
                "force": False,
            },
        )

        enqueued += 1

    logger.info(
        "AI summaries enqueued",
        extra={
            "event": "ai_summaries_enqueued",
            "requested_count": len(place_ids),
            "limit": effective_limit,
            "enqueued_count": enqueued,
            "force": force,
        },
    )

    return enqueued