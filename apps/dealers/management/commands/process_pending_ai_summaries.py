from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.management.base import BaseCommand
from apps.dealers.models import DealerAiSummary
from apps.dealers.services.dealer_ai_service import generate_ai_summary_for_dealer


class Command(BaseCommand):
    help = "Generate AI summaries for pending dealers."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--workers", type=int, default=5)

    def handle(self, *args, **options):
        limit = options["limit"]
        workers = options["workers"]

        pending = list(
            DealerAiSummary.objects
            .select_related("dealer")
            .filter(status=DealerAiSummary.STATUS_PENDING)
            .order_by("updated_at")[:limit]
        )

        total = done = failed = 0

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(generate_ai_summary_for_dealer, item.dealer): item
                for item in pending
            }
            for future in as_completed(futures):
                item = futures[future]
                total += 1
                try:
                    result = future.result()
                    if result.status == DealerAiSummary.STATUS_DONE:
                        done += 1
                        self.stdout.write(self.style.SUCCESS(f"[DONE] dealer={item.dealer.name}"))
                    else:
                        failed += 1
                        self.stdout.write(self.style.WARNING(f"[FAILED] dealer={item.dealer.name}"))
                except Exception as exc:
                    failed += 1
                    self.stdout.write(self.style.ERROR(f"[ERROR] dealer={item.dealer.name}: {exc}"))

        self.stdout.write(self.style.SUCCESS(f"Finished. total={total} done={done} failed={failed}"))