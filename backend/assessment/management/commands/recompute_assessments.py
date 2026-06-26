"""Recompute condition assessments for all structures.

Later wired to events / celery beat (#19/#20); for now an explicit command.
"""
from collections import Counter

from django.core.management.base import BaseCommand

from catalog.models import Structure

from ...services import save_assessment


class Command(BaseCommand):
    help = "Recompute ConditionAssessment for every structure."

    def handle(self, *args, **options):
        condition_counts = Counter()
        repair_counts = Counter()
        flood_counts = Counter()
        low_water_counts = Counter()
        forecast_cross = 0
        total = 0
        overdue = 0
        qs = Structure.objects.select_related("type").prefetch_related("inspections")
        for structure in qs.iterator(chunk_size=500):
            condition, repair, _due, breakdown = save_assessment(structure)
            condition_counts[condition] += 1
            repair_counts[repair] += 1
            if breakdown["interval"]["overdue"]:
                overdue += 1
            risk = breakdown.get("risk") or {}
            detectors = risk.get("detectors") or {}
            if detectors:
                flood_counts[detectors["flood"]["level"]] += 1
                low_water_counts[detectors["low_water"]["level"]] += 1
                if detectors["forecast"].get("crosses_danger"):
                    forecast_cross += 1
            total += 1

        self.stdout.write(self.style.SUCCESS(f"Recomputed {total} structures."))
        self.stdout.write("By condition_status: " + dict_str(condition_counts))
        self.stdout.write("By repair_status:    " + dict_str(repair_counts))
        self.stdout.write(f"Overdue inspections: {overdue}")
        self.stdout.write("Flood risk:     " + dict_str(flood_counts))
        self.stdout.write("Low-water risk: " + dict_str(low_water_counts))
        self.stdout.write(f"Forecast crosses danger in horizon: {forecast_cross}")


def dict_str(counter: Counter) -> str:
    return ", ".join(f"{k}={v}" for k, v in sorted(counter.items()))
