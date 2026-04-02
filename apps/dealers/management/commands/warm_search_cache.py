from django.core.management.base import BaseCommand

from apps.dealers.models import PopularSearch
from apps.dealers.services.dealer_service import search_dealers
from apps.dealers.services.google_places import is_google_cap_reached


DEFAULT_RADII = (20, 50)


class Command(BaseCommand):
    help = "Warm dealer search cache for popular cities."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="How many popular cities to warm. Default: 10",
        )
        parser.add_argument(
            "--radii",
            type=int,
            nargs="+",
            default=list(DEFAULT_RADII),
            help="Radii to warm for each city. Example: --radii 20 50",
        )
        parser.add_argument(
            "--min-count",
            type=int,
            default=1,
            help="Only warm cities with PopularSearch.count >= min-count. Default: 1",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        radii = options["radii"]
        min_count = options["min_count"]

        cities = list(
            PopularSearch.objects.filter(count__gte=min_count)
            .order_by("-count", "-updated_at", "city")
            .values_list("city", flat=True)[:limit]
        )

        if not cities:
            self.stdout.write(self.style.WARNING("No popular cities found. Nothing to warm."))
            return

        self.stdout.write(f"Starting cache warm-up for {len(cities)} cities.")
        self.stdout.write(f"Radii: {', '.join(str(r) for r in radii)} km")

        total_jobs = 0
        warmed_jobs = 0
        cache_hits = 0
        failures = 0

        for city in cities:
            for radius in radii:
                total_jobs += 1

                if is_google_cap_reached():
                    self.stdout.write(
                        self.style.WARNING(
                            "Google API daily cap reached. Stopping warm-up."
                        )
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Done early. total={total_jobs} warmed={warmed_jobs} hits={cache_hits} failures={failures}"
                        )
                    )
                    return

                try:
                    dealers, from_cache = search_dealers(city=city, radius=radius)

                    if from_cache:
                        cache_hits += 1
                        self.stdout.write(
                            f"[HIT] city={city} radius={radius} results={len(dealers)}"
                        )
                    else:
                        warmed_jobs += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"[MISS->WARMED] city={city} radius={radius} results={len(dealers)}"
                            )
                        )

                except Exception as exc:
                    failures += 1
                    self.stderr.write(
                        self.style.ERROR(
                            f"[ERROR] city={city} radius={radius} error={exc}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Warm-up finished. total={total_jobs} warmed={warmed_jobs} hits={cache_hits} failures={failures}"
            )
        )