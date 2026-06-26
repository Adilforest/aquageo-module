"""Hydropost time-series: transfer the real anchor + generate demo history (#19).

Generation is deterministic (seeded per structure) so tests are reproducible.
Level follows a seasonal base (flood Apr–Jun, low water Jul–Sep) plus an AR(1)
random walk anchored to the real ``level_mean``. A subset of posts ("breachers")
reach/exceed their danger level during the flood peak so the flood detector (#18)
has data to fire on. Discharge is monotonic in level; water temperature is a soft
seasonal curve.
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime, time, timedelta
from random import Random

from django.utils import timezone

from .models import HydropostReading

HORIZON_DAYS = 90
AR_RHO = 0.7  # AR(1) inertia

# Seasonal level multipliers vs the reference level (ref = real level_mean).
# Breachers swing wider in the flood season.
_SEASON_BREACHER = {4: 1.18, 5: 1.35, 6: 1.18, 7: 0.90, 8: 0.85, 9: 0.88}
_SEASON_CALM = {4: 1.06, 5: 1.12, 6: 1.06, 7: 0.92, 8: 0.90, 9: 0.92}

_TEMP_BY_MONTH = {1: 1, 2: 1, 3: 5, 4: 10, 5: 15, 6: 20, 7: 23, 8: 22, 9: 17, 10: 11, 11: 5, 12: 2}


def _num(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _seed(pk) -> int:
    return int(hashlib.sha256(str(pk).encode("utf-8")).hexdigest()[:8], 16)


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).strip().split(" ")[0]).date()
    except (TypeError, ValueError):
        return None


def post_params(structure) -> dict:
    """Deterministic per-post parameters (reference level, danger, etc.)."""
    attrs = structure.attributes or {}
    ref = _num(attrs.get("level_mean")) or 100.0
    if ref <= 0:
        ref = 100.0
    rng = Random(_seed(structure.pk))
    breacher = rng.random() < 0.35
    danger_factor = rng.uniform(1.05, 1.15) if breacher else rng.uniform(1.25, 1.6)
    danger = round(ref * danger_factor, 2)
    base_q = rng.uniform(5.0, 50.0)  # discharge at the reference level
    return {"ref": ref, "danger": danger, "breacher": breacher, "base_q": base_q}


def _discharge(level: float, ref: float, base_q: float) -> float:
    return round(base_q * (max(level, 0.0) / ref) ** 1.5, 2)


def _status(level: float, danger: float) -> str:
    if level >= danger:
        return "danger"
    if level >= 0.85 * danger:
        return "unfavorable"
    return "low"


def _aware(d: date) -> datetime:
    return timezone.make_aware(datetime.combine(d, time(0, 0)))


def transfer_real_anchor(structure):
    """Create the single real (synthetic=False) reading from attributes. Idempotent."""
    if getattr(structure, "type_id", None) != "hydropost":
        return None
    existing = structure.readings.filter(synthetic=False).first()
    if existing:
        return existing
    attrs = structure.attributes or {}
    level = _num(attrs.get("level_mean"))
    if level is None:
        return None  # no real measurement to anchor
    p = post_params(structure)
    anchor_date = _parse_date(attrs.get("date")) or date.today()
    return HydropostReading.objects.create(
        structure=structure,
        ts=_aware(anchor_date),
        water_level=level,
        danger_level=p["danger"],
        discharge=_discharge(level, p["ref"], p["base_q"]),
        water_temp=_num(attrs.get("water_temp")),
        status_code=str(attrs.get("danger_level") or ""),
        synthetic=False,
    )


def generate_history(structure, end_date: date | None = None, days: int = HORIZON_DAYS) -> int:
    """Regenerate synthetic daily history for the 90 days before the anchor.

    Deletes prior synthetic points (keeps the real anchor) for idempotency.
    """
    p = post_params(structure)
    ref, danger, base_q = p["ref"], p["danger"], p["base_q"]
    season = _SEASON_BREACHER if p["breacher"] else _SEASON_CALM

    if end_date is None:
        anchor = structure.readings.filter(synthetic=False).first()
        end_date = anchor.ts.date() if anchor else date.today()

    structure.readings.filter(synthetic=True).delete()

    rng = Random(_seed(structure.pk) + 1)  # separate stream from post_params
    e = 0.0
    rows = []
    for i in range(days, 0, -1):
        d = end_date - timedelta(days=i)
        e = AR_RHO * e + rng.gauss(0, 0.03 * ref)
        level = max(0.0, ref * season.get(d.month, 1.0) + e)
        temp = _TEMP_BY_MONTH[d.month] + rng.uniform(-1.0, 1.0)
        rows.append(HydropostReading(
            structure=structure,
            ts=_aware(d),
            water_level=round(level, 2),
            danger_level=danger,
            discharge=_discharge(level, ref, base_q),
            water_temp=round(temp, 1),
            status_code=_status(level, danger),
            synthetic=True,
        ))
    HydropostReading.objects.bulk_create(rows)
    return len(rows)
