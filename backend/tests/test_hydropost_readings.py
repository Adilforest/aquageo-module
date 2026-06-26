"""HydropostReading model, transfer, generation, API, override (PostGIS)."""
import datetime
import uuid

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from assessment.services import compute_assessment
from catalog.models import ObjectType, Structure
from monitoring.models import HydropostReading
from monitoring.services import generate_history, post_params, transfer_real_anchor

# 90-day window ending 2025-08-01 -> covers flood (May/Jun) and low water (Jul).
END = datetime.date(2025, 8, 1)


@pytest.fixture
def hydropost_type(db):
    return ObjectType.objects.create(code="hydropost", name_ru="Гидропост", geometry_kind="point")


def mk_post(htype, k, level_mean=200, **attrs):
    attributes = {"level_mean": level_mean, **attrs}
    return Structure.objects.create(
        id=uuid.UUID(int=k), type=htype, name_ru=f"HP{k}",
        attributes=attributes, commissioning_year=2010,
    )


@pytest.mark.django_db
def test_transfer_real_anchor(hydropost_type):
    s = mk_post(hydropost_type, 1, level_mean=150, water_temp=12,
                danger_level="danger", date="2026-05-01")
    anchor = transfer_real_anchor(s)
    assert anchor.synthetic is False
    assert anchor.water_level == 150
    assert anchor.ts.date() == datetime.date(2026, 5, 1)
    assert anchor.status_code == "danger"
    assert s.readings.filter(synthetic=False).count() == 1
    # idempotent
    transfer_real_anchor(s)
    assert s.readings.filter(synthetic=False).count() == 1


@pytest.mark.django_db
def test_generate_history_count_and_idempotency(hydropost_type):
    s = mk_post(hydropost_type, 2, level_mean=180, date="2026-05-01")
    transfer_real_anchor(s)
    assert generate_history(s, end_date=END) == 90
    assert s.readings.filter(synthetic=True).count() == 90
    # re-run does not multiply; real anchor preserved
    generate_history(s, end_date=END)
    assert s.readings.filter(synthetic=True).count() == 90
    assert s.readings.filter(synthetic=False).count() == 1


@pytest.mark.django_db
def test_flood_profile_reaches_danger_for_breachers_only(hydropost_type):
    posts = [mk_post(hydropost_type, k, level_mean=200) for k in range(1, 13)]
    breacher = next(p for p in posts if post_params(p)["breacher"])
    calm = next(p for p in posts if not post_params(p)["breacher"])

    generate_history(breacher, end_date=END)
    generate_history(calm, end_date=END)

    br = list(breacher.readings.filter(synthetic=True))
    danger_b = post_params(breacher)["danger"]
    assert any(r.water_level >= danger_b for r in br)  # breaches danger in flood

    flood = [r.water_level for r in br if r.ts.month in (4, 5, 6)]
    low = [r.water_level for r in br if r.ts.month in (7, 8, 9)]
    assert max(flood) > max(low)  # flood higher than low water
    flood_q = [r.discharge for r in br if r.ts.month in (5, 6)]
    low_q = [r.discharge for r in br if r.ts.month == 7]
    assert max(flood_q) > max(low_q)  # discharge lower in low water

    danger_c = post_params(calm)["danger"]
    assert not any(r.water_level >= danger_c for r in calm.readings.filter(synthetic=True))


@pytest.mark.django_db
def test_readings_api_returns_series(hydropost_type):
    s = mk_post(hydropost_type, 3, level_mean=180, date="2026-05-01")
    transfer_real_anchor(s)
    generate_history(s, end_date=END)
    resp = APIClient().get(f"/api/v1/structures/{s.id}/readings/")
    assert resp.status_code == 200
    assert resp.data["count"] == 91  # 90 synthetic + 1 real
    first = resp.data["results"][0]
    assert "synthetic" in first and "water_level" in first
    # ascending by ts
    ts_values = [r["ts"] for r in resp.data["results"]]
    assert ts_values == sorted(ts_values)


@pytest.mark.django_db
def test_assessment_override_uses_latest_reading(hydropost_type):
    s = mk_post(hydropost_type, 4, level_mean=100, wear_percent=5)
    # older reading below danger, newest above -> override uses the newest
    HydropostReading.objects.create(
        structure=s, ts=timezone.now() - datetime.timedelta(days=2),
        water_level=100, danger_level=250, synthetic=True,
    )
    HydropostReading.objects.create(
        structure=s, ts=timezone.now(), water_level=300, danger_level=250, synthetic=True,
    )
    _, repair, _, br = compute_assessment(s)
    assert repair == "critical"
    assert "hydropost_danger_level" in br["overrides"]
