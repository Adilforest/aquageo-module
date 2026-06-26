"""Condition assessment tests: pure function + persistence + API (PostGIS)."""
import datetime

import pytest
from django.contrib.gis.geos import Point

from assessment.models import ConditionAssessment
from assessment.services import compute_assessment, save_assessment
from catalog.models import ConditionStatus, Inspection, ObjectType, Structure

THIS_YEAR = datetime.date.today().year


@pytest.fixture
def types(db):
    return {
        "canal": ObjectType.objects.create(code="canal", name_ru="Канал", geometry_kind="line"),
        "hydropost": ObjectType.objects.create(
            code="hydropost", name_ru="Гидропост", geometry_kind="point"
        ),
    }


def mk(types, code="canal", **kwargs):
    kwargs.setdefault("name_ru", "S")
    kwargs.setdefault("attributes", {})
    return Structure.objects.create(type=types[code], **kwargs)


# --- base from wear ---
@pytest.mark.django_db
def test_wear_85_is_emergency(types):
    s = mk(types, wear_percent=85, commissioning_year=THIS_YEAR - 5)
    cond, _, br = compute_assessment(s)
    assert cond == ConditionStatus.EMERGENCY
    assert br["base"] == ConditionStatus.EMERGENCY


@pytest.mark.django_db
def test_wear_10_young_ok_inspection_is_serviceable(types):
    s = mk(types, wear_percent=10, commissioning_year=THIS_YEAR - 3)
    Inspection.objects.create(
        structure=s, inspected_at=datetime.date.today(),
        condition_observed=ConditionStatus.SERVICEABLE,
    )
    cond, repair, br = compute_assessment(s)
    assert cond == ConditionStatus.SERVICEABLE
    assert repair == "norm"
    assert br["escalation_total"] == 0


@pytest.mark.django_db
def test_wear_30_is_monitoring(types):
    s = mk(types, wear_percent=30, commissioning_year=THIS_YEAR - 3)
    Inspection.objects.create(
        structure=s, inspected_at=datetime.date.today(),
        condition_observed=ConditionStatus.SERVICEABLE,
    )
    cond, _, _ = compute_assessment(s)
    assert cond == ConditionStatus.MONITORING


@pytest.mark.django_db
def test_wear_50_bad_inspection_two_accidents_escalates(types):
    s = mk(types, wear_percent=50, commissioning_year=THIS_YEAR - 5)
    # two emergency inspections; latest is unsatisfactory
    Inspection.objects.create(
        structure=s, inspected_at=datetime.date.today() - datetime.timedelta(days=100),
        condition_observed=ConditionStatus.EMERGENCY,
    )
    Inspection.objects.create(
        structure=s, inspected_at=datetime.date.today(),
        condition_observed=ConditionStatus.EMERGENCY,
    )
    cond, _, br = compute_assessment(s)
    # base repair (wear 50); E = last(+2) + accidents>=2(+2) = 4 -> +1 level -> emergency
    assert br["escalation_total"] >= 3
    assert cond in (ConditionStatus.REPAIR, ConditionStatus.EMERGENCY)
    assert cond == ConditionStatus.EMERGENCY


@pytest.mark.django_db
def test_unknown_wear_uses_age(types):
    young = mk(types, commissioning_year=THIS_YEAR - 10)
    Inspection.objects.create(
        structure=young, inspected_at=datetime.date.today(),
        condition_observed=ConditionStatus.SERVICEABLE,
    )
    cond, _, br = compute_assessment(young)
    assert br["base_source"] == "age"
    assert br["base"] == ConditionStatus.SERVICEABLE
    assert cond == ConditionStatus.SERVICEABLE

    old = mk(types, commissioning_year=THIS_YEAR - 60)
    cond_old, _, br_old = compute_assessment(old)
    assert br_old["base_source"] == "age"
    assert br_old["base"] == ConditionStatus.REPAIR


# --- repair status mapping ---
@pytest.mark.django_db
@pytest.mark.parametrize(
    "wear,expected_condition,expected_repair",
    [
        (10, ConditionStatus.SERVICEABLE, "norm"),
        (30, ConditionStatus.MONITORING, "inspect"),
        (50, ConditionStatus.REPAIR, "repair"),
        (90, ConditionStatus.EMERGENCY, "critical"),
    ],
)
def test_repair_status_mapping(types, wear, expected_condition, expected_repair):
    s = mk(types, wear_percent=wear, commissioning_year=THIS_YEAR - 3)
    Inspection.objects.create(
        structure=s, inspected_at=datetime.date.today(),
        condition_observed=ConditionStatus.SERVICEABLE,
    )
    cond, repair, _ = compute_assessment(s)
    assert cond == expected_condition
    assert repair == expected_repair


# --- hydropost override ---
@pytest.mark.django_db
def test_hydropost_level_over_danger_is_critical_even_if_serviceable(types):
    s = mk(
        types, code="hydropost", wear_percent=5, commissioning_year=THIS_YEAR - 2,
        geom=Point(71.0, 43.0, srid=4326),
        attributes={"level_mean": 320, "danger": 250},
    )
    Inspection.objects.create(
        structure=s, inspected_at=datetime.date.today(),
        condition_observed=ConditionStatus.SERVICEABLE,
    )
    cond, repair, br = compute_assessment(s)
    assert cond == ConditionStatus.SERVICEABLE
    assert repair == "critical"
    assert "hydropost_danger_level" in br["overrides"]


@pytest.mark.django_db
def test_hydropost_level_below_danger_not_overridden(types):
    s = mk(
        types, code="hydropost", wear_percent=5, commissioning_year=THIS_YEAR - 2,
        attributes={"level_mean": 100, "danger": 250},
    )
    Inspection.objects.create(
        structure=s, inspected_at=datetime.date.today(),
        condition_observed=ConditionStatus.SERVICEABLE,
    )
    _, repair, br = compute_assessment(s)
    assert repair == "norm"
    assert br["overrides"] == []


# --- persistence + API ---
@pytest.mark.django_db
def test_save_assessment_updates_structure_and_creates_record(types):
    s = mk(types, wear_percent=85, commissioning_year=THIS_YEAR - 5, condition_status="serviceable")
    save_assessment(s)
    s.refresh_from_db()
    assert s.condition_status == ConditionStatus.EMERGENCY
    assert ConditionAssessment.objects.filter(structure=s).count() == 1
    # re-run is idempotent (update, not insert)
    save_assessment(s)
    assert ConditionAssessment.objects.filter(structure=s).count() == 1


@pytest.mark.django_db
def test_detail_api_exposes_repair_status_and_breakdown(types):
    from rest_framework.test import APIClient

    s = mk(types, wear_percent=50, commissioning_year=THIS_YEAR - 5,
           geom=Point(71.0, 43.0, srid=4326))
    save_assessment(s)
    data = APIClient().get(f"/api/v1/structures/{s.pk}/").data
    assert data["repair_status"] == "repair"
    assert data["assessment_breakdown"]["base"] == ConditionStatus.REPAIR
    assert "factors" in data["assessment_breakdown"]


@pytest.mark.django_db
def test_condition_status_not_editable_via_patch(types):
    from django.contrib.auth import get_user_model
    from rest_framework.test import APIClient

    from accounts.models import Role

    s = mk(types, wear_percent=85, commissioning_year=THIS_YEAR - 5)
    save_assessment(s)
    s.refresh_from_db()
    get_user_model().objects.create_user("e", password="p", role=Role.ENGINEER)
    c = APIClient()
    token = APIClient().post(
        "/api/v1/auth/login/", {"username": "e", "password": "p"}, format="json"
    ).data["access"]
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    c.patch(f"/api/v1/structures/{s.pk}/", {"condition_status": "serviceable"}, format="json")
    s.refresh_from_db()
    assert s.condition_status == ConditionStatus.EMERGENCY  # unchanged
