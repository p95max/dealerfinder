import logging
from celery import shared_task

from apps.dealers.models import Dealer
from apps.dealers.services.dealer_ai_service import generate_ai_summary_for_dealer
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
    except Exception as e:
        raise self.retry(exc=e, countdown=60)