import logging

from celery import shared_task

from apps.dealers.models import Dealer, DealerAiSummary
from apps.dealers.ai.service import (
    can_retry_failed_summary,
    generate_ai_summary_for_dealer,
    is_stale_pending_summary, is_stale_done_summary,
)
from apps.users.models import User

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_dealer_ai_summary_task(self, place_id, user_id=None, client_ip=None):
    try:
        dealer = Dealer.objects.get(google_place_id=place_id)
    except Dealer.DoesNotExist:
        logger.warning(
            "AI summary task skipped: dealer not found",
            extra={
                "event": "ai_summary_task_skipped_dealer_not_found",
                "place_id": place_id,
                "user_id": user_id,
                "client_ip": client_ip,
            },
        )
        return {
            "place_id": place_id,
            "status": "skipped",
            "reason": "dealer_not_found",
        }

    user = None
    if user_id:
        user = User.objects.filter(pk=user_id).first()

    try:
        result = generate_ai_summary_for_dealer(
            dealer,
            user=user,
            client_ip=client_ip,
        )

        logger.info(
            "AI summary task finished",
            extra={
                "event": "ai_summary_task_finished",
                "dealer_id": dealer.id,
                "place_id": dealer.google_place_id,
                "summary_status": result.status,
                "user_id": user.id if user else None,
                "client_ip": client_ip,
            },
        )

        return {
            "dealer_id": dealer.id,
            "place_id": dealer.google_place_id,
            "status": result.status,
        }
    except Exception as exc:
        logger.exception(
            "AI summary task failed, scheduling retry",
            extra={
                "event": "ai_summary_task_retry_scheduled",
                "dealer_id": dealer.id,
                "place_id": dealer.google_place_id,
                "user_id": user.id if user else None,
                "client_ip": client_ip,
                "retry_count": self.request.retries + 1,
            },
        )
        raise self.retry(exc=exc, countdown=60)


def _get_retry_reason(summary: DealerAiSummary) -> str | None:

    if (
        summary.status == DealerAiSummary.STATUS_FAILED
        and can_retry_failed_summary(summary)
    ):
        return "failed"

    if (
        summary.status == DealerAiSummary.STATUS_PENDING
        and is_stale_pending_summary(summary)
    ):
        return "pending_stale"

    return None


@shared_task
def retry_dealer_ai_summaries_task(limit: int = 20) -> int:
    """
    Retry failed AI summaries after cooldown and stale pending summaries.

    This task does not handle stale DONE summaries. That is handled by
    resync_stale_ai_summaries_task().
    """
    candidates = list(
        DealerAiSummary.objects.select_related("dealer")
        .filter(
            status__in=[
                DealerAiSummary.STATUS_FAILED,
                DealerAiSummary.STATUS_PENDING,
            ]
        )
        .order_by("updated_at")[: limit * 5]
    )

    retry_items: list[dict] = []

    for summary in candidates:
        reason = _get_retry_reason(summary)
        if not reason:
            continue

        retry_items.append(
            {
                "place_id": summary.dealer.google_place_id,
                "dealer_id": summary.dealer_id,
                "dealer_name": summary.dealer.name,
                "reason": reason,
                "status": summary.status,
            }
        )

        if len(retry_items) >= limit:
            break

    logger.info(
        "AI summary retry sweep started",
        extra={
            "event": "ai_summary_retry_sweep_started",
            "candidate_count": len(candidates),
            "retry_count": len(retry_items),
            "place_ids": [item["place_id"] for item in retry_items],
            "reasons": [item["reason"] for item in retry_items],
        },
    )

    dispatched = 0

    for item in retry_items:
        result = generate_dealer_ai_summary_task.delay(place_id=item["place_id"])

        logger.info(
            "AI summary retry task dispatched",
            extra={
                "event": "ai_summary_retry_task_dispatched",
                "place_id": item["place_id"],
                "dealer_id": item["dealer_id"],
                "dealer_name": item["dealer_name"],
                "reason": item["reason"],
                "previous_status": item["status"],
                "task_id": result.id,
            },
        )

        dispatched += 1

    logger.info(
        "AI summary retry sweep finished",
        extra={
            "event": "ai_summary_retry_sweep_finished",
            "limit": limit,
            "dispatched_count": dispatched,
            "retry_items": retry_items,
        },
    )

    return dispatched


@shared_task
def resync_stale_ai_summaries_task(limit: int = 20) -> int:
    """
    Periodically re-generate stale successful AI summaries.

    This keeps existing summaries reasonably fresh without relying only on
    user-triggered regeneration.
    """
    candidates = list(
        DealerAiSummary.objects.select_related("dealer")
        .filter(status=DealerAiSummary.STATUS_DONE)
        .order_by("generated_at", "updated_at")[: limit * 5]
    )

    resync_items: list[dict] = []

    for summary in candidates:
        if not is_stale_done_summary(summary):
            continue

        resync_items.append(
            {
                "place_id": summary.dealer.google_place_id,
                "dealer_id": summary.dealer_id,
                "dealer_name": summary.dealer.name,
                "generated_at": summary.generated_at.isoformat()
                if summary.generated_at
                else None,
            }
        )

        if len(resync_items) >= limit:
            break

    logger.info(
        "AI summary stale resync sweep started",
        extra={
            "event": "ai_summary_stale_resync_sweep_started",
            "candidate_count": len(candidates),
            "resync_count": len(resync_items),
            "place_ids": [item["place_id"] for item in resync_items],
        },
    )

    dispatched = 0

    for item in resync_items:
        result = generate_dealer_ai_summary_task.delay(place_id=item["place_id"])

        logger.info(
            "AI summary stale resync task dispatched",
            extra={
                "event": "ai_summary_stale_resync_task_dispatched",
                "place_id": item["place_id"],
                "dealer_id": item["dealer_id"],
                "dealer_name": item["dealer_name"],
                "generated_at": item["generated_at"],
                "task_id": result.id,
            },
        )

        dispatched += 1

    logger.info(
        "AI summary stale resync sweep finished",
        extra={
            "event": "ai_summary_stale_resync_sweep_finished",
            "limit": limit,
            "dispatched_count": dispatched,
            "resync_items": resync_items,
        },
    )

    return dispatched