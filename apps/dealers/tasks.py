import logging

from celery import shared_task

from apps.dealers.models import Dealer, DealerAiSummary
from apps.dealers.ai.service import (
    can_retry_failed_summary,
    generate_ai_summary_for_dealer,
    is_stale_pending_summary,
)
from apps.users.models import User

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_dealer_ai_summary_task(self, place_id, user_id=None, client_ip=None):
    try:
        dealer = Dealer.objects.get(google_place_id=place_id)
    except Dealer.DoesNotExist:
        return

    user = None
    if user_id:
        user = User.objects.filter(pk=user_id).first()

    try:
        generate_ai_summary_for_dealer(
            dealer,
            user=user,
            client_ip=client_ip,
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@shared_task
def retry_dealer_ai_summaries_task(limit: int = 20):
    candidates = list(
        DealerAiSummary.objects.select_related("dealer").order_by("updated_at")[: limit * 3]
    )

    retried = 0

    for item in candidates:
        should_retry = (
            item.status == DealerAiSummary.STATUS_PENDING
            and is_stale_pending_summary(item)
        ) or (
            item.status == DealerAiSummary.STATUS_FAILED
            and can_retry_failed_summary(item)
        )

        if not should_retry:
            continue

        generate_dealer_ai_summary_task.delay(place_id=item.dealer.google_place_id)
        retried += 1

        if retried >= limit:
            break

    logger.info(
        "AI summary retry sweep finished",
        extra={
            "event": "ai_summary_retry_sweep_finished",
            "limit": limit,
            "retried": retried,
        },
    )

    return retried