from concurrent.futures import ThreadPoolExecutor, as_completed

from django.core.management.base import BaseCommand

from apps.dealers.models import DealerAiSummary
from apps.dealers.ai.service import (
    can_retry_failed_summary,
    generate_ai_summary_for_dealer,
    is_stale_pending_summary,
)


class Command(BaseCommand):
    help = "Retry stale pending and retryable failed AI summaries."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--workers", type=int, default=5)

    def handle(self, *args, **options):
        limit = options["limit"]
        workers = options["workers"]

        candidates = list(
            DealerAiSummary.objects.select_related("dealer")
            .order_by("updated_at")[: limit * 3]
        )

        candidates = [
            item
            for item in candidates
            if (
                item.status == DealerAiSummary.STATUS_PENDING
                and is_stale_pending_summary(item)
            )
            or (
                item.status == DealerAiSummary.STATUS_FAILED
                and can_retry_failed_summary(item)
            )
        ][:limit]

        if not candidates:
            self.stdout.write(
                self.style.WARNING("No retryable AI summary candidates found.")
            )
            return

        total = 0
        done = 0
        failed = 0
        skipped = 0

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
                            self.style.SUCCESS(f"[DONE] dealer={item.dealer.name}")
                        )
                    elif result.status == DealerAiSummary.STATUS_FAILED:
                        failed += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"[FAILED] dealer={item.dealer.name} error={result.last_error}"
                            )
                        )
                    else:
                        skipped += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"[SKIPPED] dealer={item.dealer.name} status={result.status}"
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
                f"Finished. total={total} done={done} failed={failed} skipped={skipped}"
            )
        )