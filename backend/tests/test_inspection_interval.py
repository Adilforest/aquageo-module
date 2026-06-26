"""Inspection-interval model tests (issue #17), deterministic via as_of (PostGIS)."""
import datetime

import pytest

from assessment.services import compute_assessment
from catalog.models import ConditionStatus, Inspection, ObjectType, Structure

OCT = datetime.date(2025, 10, 15)  # non-flood month
MAY = datetime.date(2025, 5, 15)  # flood month (April–June)


@pytest.fixture
def types(db):
    return {
        code: ObjectType.objects.create(code=code, name_ru=code, geometry_kind="point")
        for code in ("canal", "hydropost", "dam")
    }


def mk(types, code="canal", inspect_on=OCT, observed=ConditionStatus.SERVICEABLE, **kwargs):
    kwargs.setdefault("name_ru", "S")
    kwargs.setdefault("attributes", {})
    kwargs.setdefault("commissioning_year", 2015)  # young by default
    s = Structure.objects.create(type=types[code], **kwargs)
    if inspect_on is not None:
        Inspection.objects.create(structure=s, inspected_at=inspect_on, condition_observed=observed)
    return s


def interval(structure, as_of=OCT):
    _, _, _, br = compute_assessment(structure, as_of=as_of)
    return br["interval"]["interval_months"]


# --- base intervals per condition (local, young, non-flood -> multipliers 1.0) ---
@pytest.mark.django_db
@pytest.mark.parametrize(
    "wear,months",
    [(10, 36), (30, 12), (50, 6), (90, 1)],
)
def test_base_intervals(types, wear, months):
    s = mk(types, wear_percent=wear, significance="local")
    assert interval(s) == months


@pytest.mark.django_db
def test_republican_emergency_min_one_month(types):
    s = mk(types, wear_percent=90, significance="republican")
    # 1 * 0.5 = 0.5 -> rounded, floored to minimum 1 month
    assert interval(s) == 1


@pytest.mark.django_db
def test_age_over_50_shortens(types):
    s = mk(types, wear_percent=10, significance="local", commissioning_year=1950)
    assert interval(s) == 27  # 36 * 0.75


# --- seasonal flood multiplier ---
@pytest.mark.django_db
def test_flood_type_shortened_in_flood_month(types):
    s = mk(types, code="hydropost", wear_percent=10, significance="local")
    assert interval(s, as_of=MAY) == 18  # 36 * 0.5
    assert interval(s, as_of=OCT) == 36  # outside flood season


@pytest.mark.django_db
def test_non_flood_type_not_shortened_in_flood_month(types):
    s = mk(types, code="canal", wear_percent=10, significance="local")
    assert interval(s, as_of=MAY) == 36  # canal is not flood-prone


# --- anchor priority ---
@pytest.mark.django_db
def test_anchor_from_last_inspection(types):
    s = mk(types, wear_percent=10, significance="local", inspect_on=datetime.date(2025, 9, 1))
    _, _, due, br = compute_assessment(s, as_of=OCT)
    assert br["interval"]["anchor_source"] == "last_inspection"
    assert due == datetime.date(2028, 9, 1)  # 2025-09-01 + 36 months


@pytest.mark.django_db
def test_anchor_from_commissioning_year_when_no_inspection(types):
    s = mk(types, wear_percent=10, significance="local", commissioning_year=2024, inspect_on=None)
    _, _, due, br = compute_assessment(s, as_of=OCT)
    assert br["interval"]["anchor_source"] == "commissioning_year"
    assert due == datetime.date(2027, 1, 1)  # 2024-01-01 + 36 months


@pytest.mark.django_db
def test_anchor_from_today_when_no_inspection_no_year(types):
    s = Structure.objects.create(type=types["canal"], name_ru="S", attributes={}, wear_percent=10)
    _, _, due, br = compute_assessment(s, as_of=OCT)
    assert br["interval"]["anchor_source"] == "today"
    assert due == datetime.date(2028, 10, 15)  # today + 36 months


# --- overdue override ---
@pytest.mark.django_db
def test_overdue_raises_repair_to_inspect(types):
    s = mk(types, wear_percent=10, significance="local", inspect_on=datetime.date(2010, 1, 1))
    cond, repair, due, br = compute_assessment(s, as_of=OCT)
    assert cond == ConditionStatus.SERVICEABLE
    assert due < OCT  # overdue
    assert repair == "inspect"
    assert "overdue_inspection" in br["overrides"]


@pytest.mark.django_db
def test_overdue_does_not_lower_already_critical(types):
    s = mk(types, wear_percent=90, significance="local", inspect_on=datetime.date(2010, 1, 1))
    _, repair, _, _ = compute_assessment(s, as_of=OCT)
    assert repair == "critical"  # emergency stays critical


@pytest.mark.django_db
def test_hydropost_danger_stays_critical(types):
    s = mk(
        types, code="hydropost", wear_percent=5, significance="local",
        attributes={"level_mean": 320, "danger": 250},
    )
    cond, repair, _, br = compute_assessment(s, as_of=OCT)
    assert cond == ConditionStatus.SERVICEABLE
    assert repair == "critical"
    assert "hydropost_danger_level" in br["overrides"]
