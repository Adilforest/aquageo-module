"""Risk detector tests (issue #18), deterministic controlled series (PostGIS)."""
import datetime

import pytest
from django.utils import timezone

from assessment.services import save_assessment
from catalog.models import ObjectType, Structure
from common.models import AuditLog
from monitoring.models import HydropostReading
from monitoring.risk import FloodDetector, ForecastDetector, LowWaterDetector, compute_risk

DANGER = 100.0
DAY = datetime.timedelta(days=1)


@pytest.fixture
def types(db):
    return {
        "hydropost": ObjectType.objects.create(
            code="hydropost", name_ru="ГП", geometry_kind="point"),
        "canal": ObjectType.objects.create(
            code="canal", name_ru="Канал", geometry_kind="line"),
    }


def make_series(structure, points, *, start_month=8, start_day=1, year=2025):
    """points: list of (water_level, discharge). One per day, ascending ts."""
    base = timezone.make_aware(datetime.datetime(year, start_month, start_day))
    for i, (level, q) in enumerate(points):
        HydropostReading.objects.create(
            structure=structure, ts=base + i * DAY, water_level=level,
            danger_level=DANGER, discharge=q, synthetic=True,
        )


def hp(types, k=1):
    import uuid
    return Structure.objects.create(id=uuid.UUID(int=k), type=types["hydropost"], name_ru=f"HP{k}",
                                    attributes={})


# --- flood ---
@pytest.mark.django_db
def test_flood_high_at_0_95(types):
    s = hp(types)
    make_series(s, [(95.0, 10.0)] * 5)  # flat at r=0.95
    res = FloodDetector().evaluate(s, list(s.readings.order_by("ts")))
    assert res["level"] == "high"


@pytest.mark.django_db
def test_flood_critical_at_or_above_danger(types):
    s = hp(types)
    make_series(s, [(100.0, 10.0)] * 5)  # r=1.0
    assert FloodDetector().evaluate(s, list(s.readings.order_by("ts")))["level"] == "critical"


@pytest.mark.django_db
def test_flood_fast_rise_escalates(types):
    s = hp(types)
    # r=0.85 (base watch) but +15% of danger over 3 days -> escalate to high
    make_series(s, [(70.0, 10.0), (75.0, 10.0), (80.0, 10.0), (85.0, 10.0)])
    res = FloodDetector().evaluate(s, list(s.readings.order_by("ts")))
    assert res["level"] == "high"
    assert any(f["code"] == "fast_rise" for f in res["factors"])


@pytest.mark.django_db
def test_flood_none_when_low_and_flat(types):
    s = hp(types)
    make_series(s, [(70.0, 10.0)] * 5)  # r=0.7, no rise
    assert FloodDetector().evaluate(s, list(s.readings.order_by("ts")))["level"] == "none"


# --- low water ---
@pytest.mark.django_db
def test_low_water_watch_at_q_0_4(types):
    s = hp(types)
    # low-water season (Aug). norm = median(discharge). Build so last q=0.4.
    pts = [(50.0, 10.0)] * 10 + [(50.0, 4.0)]  # median ~10, last 4 -> q=0.4
    make_series(s, pts, start_month=8)
    assert LowWaterDetector().evaluate(s, list(s.readings.order_by("ts")))["level"] == "watch"


@pytest.mark.django_db
def test_low_water_high_below_0_3(types):
    s = hp(types)
    pts = [(50.0, 10.0)] * 10 + [(50.0, 2.0)]  # q=0.2
    make_series(s, pts, start_month=8)
    assert LowWaterDetector().evaluate(s, list(s.readings.order_by("ts")))["level"] == "high"


@pytest.mark.django_db
def test_low_water_sustained_escalates(types):
    s = hp(types)
    # enough high points keep the seasonal median ~10, then 14 sustained lows
    # (q=0.4 -> watch) escalated by the streak -> high
    pts = [(50.0, 10.0)] * 30 + [(50.0, 4.0)] * 14
    make_series(s, pts, start_month=8)
    res = LowWaterDetector().evaluate(s, list(s.readings.order_by("ts")))
    assert res["level"] == "high"
    assert any(f["code"] == "sustained" for f in res["factors"])


@pytest.mark.django_db
def test_low_water_seasonal_norm_no_false_drought(types):
    s = hp(types)
    # All readings in the low-water season at the same level -> q≈1 -> none
    make_series(s, [(50.0, 6.0)] * 20, start_month=8)
    assert LowWaterDetector().evaluate(s, list(s.readings.order_by("ts")))["level"] == "none"


# --- forecast ---
@pytest.mark.django_db
def test_forecast_rising_series_crosses_danger(types):
    s = hp(types)
    make_series(s, [(80.0 + i, 10.0) for i in range(14)])  # rising 80..93
    res = ForecastDetector().evaluate(s, list(s.readings.order_by("ts")))
    assert res["estimated"] is True
    assert res["crosses_danger"] is True
    assert res["crossing_day"] is not None
    assert res["predicted"][-1] > res["predicted"][0]  # forecast rising


@pytest.mark.django_db
def test_forecast_flat_series_no_crossing(types):
    s = hp(types)
    make_series(s, [(50.0, 10.0)] * 14)
    res = ForecastDetector().evaluate(s, list(s.readings.order_by("ts")))
    assert res["crosses_danger"] is False
    assert res["estimated"] is True


# --- integration ---
@pytest.mark.django_db
def test_compute_risk_empty_for_non_hydropost(types):
    canal = Structure.objects.create(type=types["canal"], name_ru="C", attributes={})
    assert compute_risk(canal) == {}


@pytest.mark.django_db
def test_save_assessment_stores_risk_and_raises_alert(types):
    s = hp(types)
    make_series(s, [(100.0, 10.0)] * 5)  # flood critical
    save_assessment(s)
    s.refresh_from_db()
    from assessment.models import ConditionAssessment
    a = ConditionAssessment.objects.get(structure=s)
    assert "risk" in a.risk_scores
    assert a.risk_scores["risk"]["detectors"]["flood"]["level"] == "critical"
    assert a.risk_scores["risk"]["alert"] is True
    assert AuditLog.objects.filter(entity_id=str(s.pk), action="risk.alert").exists()


@pytest.mark.django_db
def test_risk_in_detail_api(types):
    from rest_framework.test import APIClient

    s = hp(types)
    make_series(s, [(95.0, 10.0)] * 5)
    save_assessment(s)
    data = APIClient().get(f"/api/v1/structures/{s.id}/").data
    assert data["risk"]["detectors"]["flood"]["level"] == "high"
    assert data["risk"]["detectors"]["forecast"]["estimated"] is True
