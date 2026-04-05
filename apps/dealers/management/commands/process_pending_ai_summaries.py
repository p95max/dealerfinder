from django.core.management.base import BaseCommand

from apps.dealers.models import DealerAiSummary
from apps.dealers.services.dealer_ai_service import generate_ai_summary_for_dealer


class Command(BaseCommand):
    help = "Generate AI summaries for pending dealers."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="How many pending summaries to process.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]

        pending = (
            DealerAiSummary.objects
            .select_related("dealer")
            .filter(status=DealerAiSummary.STATUS_PENDING)
            .order_by("updated_at")[:limit]
        )

        total = 0
        done = 0
        failed = 0

        for item in pending:
            total += 1
            result = generate_ai_summary_for_dealer(item.dealer)

            if result.status == DealerAiSummary.STATUS_DONE:
                done += 1
                self.stdout.write(self.style.SUCCESS(f"[DONE] dealer={item.dealer.name}"))
            else:
                failed += 1
                self.stdout.write(self.style.WARNING(f"[FAILED] dealer={item.dealer.name}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished. total={total} done={done} failed={failed}"
            )
        )