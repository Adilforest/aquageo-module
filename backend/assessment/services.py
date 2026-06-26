"""Condition assessment + inspection-interval model (issues #16, #17).

Pure function ``compute_assessment(structure, as_of=today)`` ->
(condition_status, repair_status, next_inspection_due, breakdown).

Thresholds/intervals/multipliers are fixed by the spec; ``breakdown``
(stored in ``risk_scores``) explains every factor for the object card.
``as_of`` parameterises "today" so seasonal logic and tests are deterministic.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from django.utils import timezone

from catalog.models import ConditionStatus

from .models import ConditionAssessment, RepairStatus

MODEL_VERSION = "condition-v2"  # v2: adds inspection interval + overdue override

# Severity ladder: serviceable < monitoring < repair < emergency.
LEVELS = [
    ConditionStatus.SERVICEABLE,
    ConditionStatus.MONITORING,
    ConditionStatus.REPAIR,
    ConditionStatus.EMERGENCY,
]

REPAIR_MAP = {
    ConditionStatus.SERVICEABLE: RepairStatus.NORM,
    ConditionStatus.MONITORING: RepairStatus.INSPECT,
    ConditionStatus.REPAIR: RepairStatus.REPAIR,
    ConditionStatus.EMERGENCY: RepairStatus.CRITICAL,
}

REPAIR_RANK = {
    RepairStatus.NORM: 0,
    RepairStatus.INSPECT: 1,
    RepairStatus.REPAIR: 2,
    RepairStatus.CRITICAL: 3,
}

# Base inspection interval in months by condition.
BASE_INTERVAL_MONTHS = {
    ConditionStatus.SERVICEABLE: 36,
    ConditionStatus.MONITORING: 12,
    ConditionStatus.REPAIR: 6,
    ConditionStatus.EMERGENCY: 1,
}

SIGNIFICANCE_MULT = {
    "republican": 0.5,
    "regional": 0.75,
    "district": 1.0,
    "local": 1.0,
}

# Flood-prone types: seasonal multiplier applies during the flood period.
FLOOD_TYPES = {"hydropost", "dam", "dike", "reservoir", "spillway"}
FLOOD_MONTHS = {4, 5, 6}  # April–June for the Jambyl region


def _base_from_wear(wear_pct: float) -> str:
    if wear_pct < 20:
        return ConditionStatus.SERVICEABLE
    if wear_pct < 40:
        return ConditionStatus.MONITORING
    if wear_pct <= 80:  # 40-60 and 60-80 both map to repair
        return ConditionStatus.REPAIR
    return ConditionStatus.EMERGENCY


def _base_from_age(age_years: int) -> str:
    if age_years < 25:
        return ConditionStatus.SERVICEABLE
    if age_years <= 50:
        return ConditionStatus.MONITORING
    return ConditionStatus.REPAIR


def _hydropost_override(structure) -> bool:
    """Hydropost is critical when the latest reading's level reaches danger.

    Source switched (#19) from Structure.attributes to the HydropostReading
    time series — uses the most recent measurement.
    """
    if getattr(structure, "type_id", None) != "hydropost":
        return False
    last = structure.readings.order_by("-ts").first()
    if last and last.water_level is not None and last.danger_level is not None:
        return last.water_level >= last.danger_level
    return False


def _add_months(d: date, months: int) -> date:
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _interval(condition, structure, age, as_of):
    """Return (interval_months, multiplier_breakdown) for the condition."""
    base = BASE_INTERVAL_MONTHS[condition]
    multipliers = []

    sig = structure.significance or ""
    sig_mult = SIGNIFICANCE_MULT.get(sig, 1.0)
    multipliers.append({"code": "significance", "factor": sig_mult, "detail": sig or "—"})

    age_mult = 0.75 if (age is not None and age > 50) else 1.0
    multipliers.append({"code": "age", "factor": age_mult,
                        "detail": f"возраст {age} лет" if age is not None else "—"})

    flood = getattr(structure, "type_id", None) in FLOOD_TYPES and as_of.month in FLOOD_MONTHS
    season_mult = 0.5 if flood else 1.0
    multipliers.append({"code": "seasonal_flood", "factor": season_mult,
                        "detail": "паводковый период" if flood else "вне паводка"})

    product = 1.0
    for m in multipliers:
        product *= m["factor"]
    interval = max(1, round(base * product))
    return interval, base, multipliers


def compute_assessment(structure, as_of: date | None = None):
    """Return (condition_status, repair_status, next_inspection_due, breakdown)."""
    if as_of is None:
        as_of = date.today()
    factors: list[dict] = []

    age = None
    if structure.commissioning_year:
        age = as_of.year - structure.commissioning_year

    # --- base from wear, else age, else serviceable ---
    wear = structure.wear_percent
    wear_pct = None
    if wear is not None:
        wear_pct = float(wear)
        if 0 < wear_pct < 1.0:  # stored as a 0..1 fraction
            wear_pct *= 100

    if wear_pct is not None:
        base = _base_from_wear(wear_pct)
        base_source = "wear"
    elif age is not None:
        base = _base_from_age(age)
        base_source = "age"
    else:
        base = ConditionStatus.SERVICEABLE
        base_source = "none"

    # --- escalation E ---
    escalation = 0
    if age is not None and age > 50:
        escalation += 1
        factors.append({"code": "age_over_50", "points": 1, "detail": f"возраст {age} лет"})

    inspections = list(structure.inspections.all())  # Meta ordering: -inspected_at
    last = inspections[0] if inspections else None

    if last and last.condition_observed:
        obs = last.condition_observed
        if obs == ConditionStatus.EMERGENCY:
            escalation += 2
            factors.append({"code": "last_inspection_unsatisfactory", "points": 2,
                            "detail": "последний осмотр: аварийное"})
        elif obs in (ConditionStatus.MONITORING, ConditionStatus.REPAIR):
            escalation += 1
            factors.append({"code": "last_inspection_remarks", "points": 1,
                            "detail": f"последний осмотр: {obs}"})

    stale_before = as_of - timedelta(days=3 * 365)
    if last is None:
        escalation += 1
        factors.append({"code": "no_inspection", "points": 1, "detail": "осмотров нет"})
    elif last.inspected_at < stale_before:
        escalation += 1
        factors.append({"code": "inspection_stale", "points": 1,
                        "detail": f"последний осмотр {last.inspected_at} (>3 лет)"})

    adverse = sum(1 for i in inspections if i.condition_observed == ConditionStatus.EMERGENCY)
    if adverse >= 2:
        escalation += 2
        factors.append({"code": "accidents", "points": 2,
                        "detail": f"аварийных осмотров: {adverse}"})
    elif adverse == 1:
        escalation += 1
        factors.append({"code": "accidents", "points": 1, "detail": "аварийных осмотров: 1"})

    # --- apply escalation to the base level ---
    if escalation >= 6:
        bump = 2
    elif escalation >= 3:
        bump = 1
    else:
        bump = 0
    final_index = min(len(LEVELS) - 1, LEVELS.index(base) + bump)
    condition = LEVELS[final_index]

    # --- repair status + hydropost override ---
    repair = REPAIR_MAP[condition]
    overrides: list[str] = []
    if _hydropost_override(structure):
        repair = RepairStatus.CRITICAL
        overrides.append("hydropost_danger_level")

    # --- inspection interval / next due ---
    interval_months, base_months, multipliers = _interval(condition, structure, age, as_of)

    if last is not None:
        anchor, anchor_source = last.inspected_at, "last_inspection"
    elif structure.commissioning_year:
        anchor, anchor_source = date(structure.commissioning_year, 1, 1), "commissioning_year"
    else:
        anchor, anchor_source = as_of, "today"
    next_due = _add_months(anchor, interval_months)

    # --- overdue override (#17): raise repair_status to at least inspect ---
    overdue = next_due < as_of
    if overdue and REPAIR_RANK[repair] < REPAIR_RANK[RepairStatus.INSPECT]:
        repair = RepairStatus.INSPECT
        overrides.append("overdue_inspection")
    elif overdue:
        overrides.append("overdue_inspection")  # already >= inspect, recorded for the card

    breakdown = {
        "model_version": MODEL_VERSION,
        "wear_percent": wear_pct,
        "age_years": age,
        "base": base,
        "base_source": base_source,
        "factors": factors,
        "escalation_total": escalation,
        "level_bump": bump,
        "condition_status": condition,
        "repair_status": repair,
        "overrides": overrides,
        "interval": {
            "base_months": base_months,
            "multipliers": multipliers,
            "interval_months": interval_months,
            "anchor": anchor.isoformat(),
            "anchor_source": anchor_source,
            "next_inspection_due": next_due.isoformat(),
            "overdue": overdue,
        },
    }
    return condition, repair, next_due, breakdown


def save_assessment(structure, as_of: date | None = None):
    """Compute and persist the current assessment; update Structure.condition_status.

    Also runs the risk detectors (#18) for hydroposts, stores their breakdown in
    risk_scores and raises a risk.alert audit event on high/critical.
    """
    from common.audit import AuditEvent, record
    from monitoring.risk import compute_risk

    condition, repair, next_due, breakdown = compute_assessment(structure, as_of)

    risk = compute_risk(structure)
    breakdown["risk"] = risk
    if risk.get("alert"):
        record(AuditEvent(
            actor="system",
            action="risk.alert",
            entity_type="structure",
            entity_id=str(structure.pk),
            payload={
                "max_level": risk["max_level"],
                "detectors": {k: v["level"] for k, v in risk["detectors"].items()},
            },
        ))

    ConditionAssessment.objects.update_or_create(
        structure=structure,
        defaults={
            "assessed_at": timezone.now(),
            "condition_status": condition,
            "repair_status": repair,
            "next_inspection_due": next_due,
            "risk_scores": breakdown,
            "model_version": MODEL_VERSION,
        },
    )
    if structure.condition_status != condition:
        structure.condition_status = condition
        structure.save(update_fields=["condition_status", "updated_at"])
    return condition, repair, next_due, breakdown
