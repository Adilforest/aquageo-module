"""Transfer real anchors and generate synthetic hydropost history (#19).

Idempotent: re-running replaces synthetic points and keeps the real anchor.
"""
from django.core.management.base import BaseCommand

from catalog.models import Structure

from ...models import HydropostReading
from ...services import generate_history, post_params, transfer_real_anchor


class Command(BaseCommand):
    help = "Generate demo time series for hydroposts (real anchor + synthetic history)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=90)

    def handle(self, *args, **opts):
        posts = Structure.objects.filter(type__code="hydropost")
        real = 0
        synthetic = 0
        flood_posts = 0
        for s in posts.iterator(chunk_size=200):
            if transfer_real_anchor(s) is not None:
                real += 1
            synthetic += generate_history(s, days=opts["days"])
            danger = post_params(s)["danger"]
            if s.readings.filter(synthetic=True, water_level__gte=danger).exists():
                flood_posts += 1

        self.stdout.write(self.style.SUCCESS(
            f"Hydroposts: {posts.count()}. Real anchors: {real}. "
            f"Synthetic points: {synthetic}. Total readings: {HydropostReading.objects.count()}."
        ))
        self.stdout.write(f"Posts whose flood profile reaches/exceeds danger: {flood_posts}")
