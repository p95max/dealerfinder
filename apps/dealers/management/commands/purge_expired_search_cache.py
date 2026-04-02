from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.dealers.models import SearchCache
from apps.dealers.services.cache_service import TTL


class Command(BaseCommand):
    help = "Delete expired SearchCache rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=None,
            help="Override cache TTL in hours. By default uses cache_service.TTL.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many rows would be deleted without deleting them.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Delete rows in batches. Default: 1000",
        )

    def handle(self, *args, **options):
        hours = options["hours"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        ttl = timedelta(hours=hours) if hours is not None else TTL
        cutoff = timezone.now() - ttl

        qs = SearchCache.objects.filter(created_at__lt=cutoff).order_by("id")
        total = qs.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS("No expired SearchCache rows found."))
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] Would delete {total} expired SearchCache rows older than {cutoff.isoformat()}."
                )
            )
            return

        deleted_total = 0

        while True:
            ids = list(qs.values_list("id", flat=True)[:batch_size])
            if not ids:
                break

            deleted_count, _ = SearchCache.objects.filter(id__in=ids).delete()
            deleted_total += deleted_count

            self.stdout.write(
                f"Deleted {deleted_total}/{total} expired SearchCache rows..."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Deleted {deleted_total} expired SearchCache rows older than {cutoff.isoformat()}."
            )
        )