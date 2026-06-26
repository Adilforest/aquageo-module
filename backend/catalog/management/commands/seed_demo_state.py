"""Make the catalog look realistic for the demo (issue #34).

Problem: the open-data import fills missing wear/condition from a hash
(``plausible_condition``), and those values land mostly in the "repair" band
under the assessment thresholds; combined with old/short inspection intervals
almost everything ends up in a bad state and "overdue". For a credible demo we
want a believable spread (most objects serviceable/monitoring, a minority in
repair/emergency).

This command *augments* the imported data (it does not delete real objects):
for a deterministic majority of structures it sets a sensible ``wear_percent``
and adds ONE fresh inspection (recent date) so the recompute produces a
realistic distribution. A minority is left untouched on purpose, so the "needs
attention" / overdue tail stays present. Re-running is idempotent: demo
inspections (tagged by ``inspector``) are removed and re-created.

Run ``recompute_assessments`` afterwards to refresh statuses.
"""
from __future__ import annotations

from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import ConditionStatus, Inspection, Structure

# Inspections created by this command carry this tag so re-runs are idempotent
# and real/import inspections are never touched.
DEMO_INSPECTOR = "Госкомиссия (демо-сид #34)"

# Target condition -> wear % that lands in that band under _base_from_wear
# (<20 serviceable, <40 monitoring, 40-80 repair, >80 emergency).
WEAR_FOR = {
    ConditionStatus.SERVICEABLE: 12,
    ConditionStatus.MONITORING: 30,
    ConditionStatus.REPAIR: 58,
    ConditionStatus.EMERGENCY: 88,
}

# Distribution (percentages, sum=100) applied across the "fresh" subset.
DISTRIBUTION = [
    (ConditionStatus.SERVICEABLE, 40),
    (ConditionStatus.MONITORING, 30),
    (ConditionStatus.REPAIR, 20),
    (ConditionStatus.EMERGENCY, 10),
]


def _cumulative(dist):
    out, acc = [], 0
    for cond, pct in dist:
        acc += pct
        out.append((cond, acc))
    return out


_CUM = _cumulative(DISTRIBUTION)


def _target_for(slot: int) -> str:
    """Map a 0..99 slot to a target condition by the cumulative distribution."""
    for cond, upper in _CUM:
        if slot < upper:
            return cond
    return _CUM[-1][0]


class Command(BaseCommand):
    help = "Augment imported objects with realistic wear + fresh inspections (demo)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fresh-share", type=float, default=0.88,
            help="Fraction of structures to give a fresh inspection (0..1). "
                 "The rest keep imported data (overdue/bad tail). Default 0.88.",
        )
        parser.add_argument(
            "--as-of", default=None,
            help="Anchor date YYYY-MM-DD for the fresh inspections (default: today).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        as_of = date.fromisoformat(options["as_of"]) if options["as_of"] else date.today()
        fresh_share = max(0.0, min(1.0, options["fresh_share"]))

        # Idempotency: drop previous demo inspections (never touch real ones).
        removed, _ = Inspection.objects.filter(inspector=DEMO_INSPECTOR).delete()

        ids = list(Structure.objects.order_by("id").values_list("id", flat=True))
        total = len(ids)
        fresh_n = int(round(total * fresh_share))

        per_target = {cond: 0 for cond, _ in DISTRIBUTION}
        new_inspections = []
        for i, sid in enumerate(ids[:fresh_n]):
            target = _target_for(i % 100)
            wear = WEAR_FOR[target]
            # Spread inspection dates over the last ~15..125 days, deterministically.
            inspected_at = as_of - timedelta(days=15 + (i % 110))
            Structure.objects.filter(pk=sid).update(wear_percent=wear)
            new_inspections.append(Inspection(
                structure_id=sid,
                inspected_at=inspected_at,
                inspector=DEMO_INSPECTOR,
                condition_observed=target,
                wear_percent=wear,
                notes="Плановый осмотр (демо-сценарий #34).",
            ))
            per_target[target] += 1

        Inspection.objects.bulk_create(new_inspections, batch_size=500)

        self.stdout.write(self.style.SUCCESS(
            f"Demo seed: {fresh_n}/{total} structures got a fresh inspection "
            f"(removed {removed} stale demo inspections; "
            f"{total - fresh_n} left untouched as the overdue/attention tail)."
        ))
        for cond, _pct in DISTRIBUTION:
            label = ConditionStatus(cond).label
            self.stdout.write(f"  fresh -> {label}: {per_target[cond]}")
        self.stdout.write(self.style.WARNING(
            "Next: run `python manage.py recompute_assessments` to refresh statuses."
        ))
