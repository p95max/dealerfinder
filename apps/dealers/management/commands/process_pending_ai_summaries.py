from concurrent.futures import ThreadPoolExecutor, as_completed

from django.core.management.base import BaseCommand

from apps.dealers.models import DealerAiSummary
from apps.dealers.services.dealer_ai_service import generate_ai_summary_for_dealer


class Command(BaseCommand):
    help = "Process AI summaries for pending, failed, and done dealers."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--workers", type=int, default=5)

    def handle(self, *args, **options):
        limit = options["limit"]
        workers = options["workers"]

        candidates = list(
            DealerAiSummary.objects.select_related("dealer")
            .filter(
                status__in=[
                    DealerAiSummary.STATUS_PENDING,
                    DealerAiSummary.STATUS_FAILED,
                    DealerAiSummary.STATUS_DONE,
                ]
            )
            .order_by("updated_at")[:limit]
        )

        if not candidates:
            self.stdout.write(self.style.WARNING("No AI summary candidates found."))
            return

        total = 0
        done = 0
        failed = 0

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(generate_ai_summary_for_dealer, item.dealer): item
                for item in candidates
            }

            for future in as_completed(futures):
                item = futures[future]
                total += 1

                try:
                    result = future.result()

                    if result.status == DealerAiSummary.STATUS_DONE:
                        done += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"[DONE] dealer={item.dealer.name}"
                            )
                        )
                    elif result.status == DealerAiSummary.STATUS_FAILED:
                        failed += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"[FAILED] dealer={item.dealer.name}"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"[SKIPPED/PENDING] dealer={item.dealer.name} status={result.status}"
                            )
                        )

                except Exception as exc:
                    failed += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"[ERROR] dealer={item.dealer.name}: {exc}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished. total={total} done={done} failed={failed}"
            )
        )