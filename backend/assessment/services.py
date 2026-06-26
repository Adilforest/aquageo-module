"""Condition assessment model (issue #16).

Pure function ``compute_assessment(structure)`` -> (condition_status,
repair_status, breakdown). Thresholds are fixed by the spec; the breakdown
(``risk_scores``) explains every factor for the object card.

NOT handled here (issue #17): inspection-overdue override and significance.
"""
from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone

from catalog.models import ConditionStatus

from .models import ConditionAssessment, RepairStatus

MODEL_VERSION = "condition-v1"

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
    """Hydropost is critical when the water level reaches the danger level.

    Primary: numeric level >= numeric danger (attributes level_mean/water_level
    vs danger/danger_level). Fallback: the qazsu categorical danger_level=="danger".
    """
    if getattr(structure, "type_id", None) != "hydropost":
        return False
    attrs = structure.attributes or {}
    level = attrs.get("water_level", attrs.get("level_mean"))
    danger = attrs.get("danger", attrs.get("danger_level"))
    try:
        if level is not None and danger is not None and float(level) >= float(danger):
            return True
    except (TypeError, ValueError):
        pass  # danger is categorical, not numeric
    return str(attrs.get("danger_level", "")).strip().lower() == "danger"


def compute_assessment(structure):
    """Return (condition_status, repair_status, breakdown) for a structure."""
    factors: list[dict] = []

    # --- age ---
    current_year = date.today().year
    age = None
    if structure.commissioning_year:
        age = current_year - structure.commissioning_year

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

    stale_before = date.today() - timedelta(days=3 * 365)
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
    }
    return condition, repair, breakdown


def save_assessment(structure):
    """Compute and persist the current assessment; update Structure.condition_status."""
    condition, repair, breakdown = compute_assessment(structure)
    ConditionAssessment.objects.update_or_create(
        structure=structure,
        defaults={
            "assessed_at": timezone.now(),
            "condition_status": condition,
            "repair_status": repair,
            "risk_scores": breakdown,
            "model_version": MODEL_VERSION,
        },
    )
    if structure.condition_status != condition:
        structure.condition_status = condition
        structure.save(update_fields=["condition_status", "updated_at"])
    return condition, repair, breakdown
