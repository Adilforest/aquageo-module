"""Dashboard aggregate endpoint tests (issue #20), PostGIS."""
import datetime

import pytest
from django.contrib.gis.geos import Point
from django.utils import timezone
from rest_framework.test import APIClient

from assessment.services import save_assessment
from catalog.models import AdminUnit, Basin, ObjectType, Structure
from monitoring.models import HydropostReading


@pytest.fixture
def world(db):
    dam = ObjectType.objects.create(code="dam", name_ru="Плотина", geometry_kind="point")
    canal = ObjectType.objects.create(code="canal", name_ru="Канал", geometry_kind="line")
    hp = ObjectType.objects.create(code="hydropost", name_ru="Гидропост", geometry_kind="point")
    basin_a = Basin.objects.create(name_ru="Шу-Таласский")
    basin_b = Basin.objects.create(name_ru="Иной")
    d1 = AdminUnit.objects.create(kato="3110", name_ru="Байзакский", level="district")

    def mk(t, name, cond, basin=basin_a, district=d1):
        return Structure.objects.create(
            type=t, name_ru=name, condition_status=cond, basin=basin, admin_unit=district,
            geom=Point(71.0, 43.0, srid=4326), attributes={},
        )

    mk(dam, "d1", "emergency")
    mk(dam, "d2", "repair")
    mk(canal, "c1", "serviceable", basin=basin_b)
    mk(canal, "c2", "monitoring")
    return {"basin_a": basin_a, "basin_b": basin_b, "hp": hp}


@pytest.mark.django_db
def test_by_type(world):
    data = APIClient().get("/api/v1/stats/by-type/").data
    by = {r["type"]: r["count"] for r in data}
    assert by == {"dam": 2, "canal": 2}


@pytest.mark.django_db
def test_by_condition_sums_to_total_and_index(world):
    data = APIClient().get("/api/v1/stats/by-condition/").data
    assert data["counts"] == {"serviceable": 1, "monitoring": 1, "repair": 1, "emergency": 1}
    assert data["total"] == 4
    assert sum(data["counts"].values()) == data["total"]
    assert data["index"] == 50  # (serviceable+monitoring)/total = 2/4


@pytest.mark.django_db
def test_by_territory_basin_and_district(world):
    basin = APIClient().get("/api/v1/stats/by-territory/", {"group": "basin"}).data
    counts = {i["name"]: i["count"] for i in basin["items"]}
    assert counts == {"Шу-Таласский": 3, "Иной": 1}
    district = APIClient().get("/api/v1/stats/by-territory/", {"group": "district"}).data
    assert district["group"] == "district"
    assert district["items"][0]["count"] == 4


@pytest.mark.django_db
def test_aggregates_respect_filters(world):
    data = APIClient().get("/api/v1/stats/by-type/", {"type": "dam"}).data
    assert {r["type"]: r["count"] for r in data} == {"dam": 2}
    cond = APIClient().get("/api/v1/stats/by-condition/", {"basin": str(world["basin_b"].pk)}).data
    assert cond["total"] == 1
    assert cond["counts"]["serviceable"] == 1


@pytest.mark.django_db
def test_risk_summary_matches_detectors(world):
    s = Structure.objects.create(
        type=world["hp"], name_ru="HP", condition_status="serviceable",
        geom=Point(71.0, 43.0, srid=4326), attributes={},
    )
    base = timezone.make_aware(datetime.datetime(2025, 5, 1))
    for i in range(5):
        HydropostReading.objects.create(
            structure=s, ts=base + datetime.timedelta(days=i),
            water_level=100, danger_level=100, discharge=10, synthetic=True,
        )
    save_assessment(s)
    data = APIClient().get("/api/v1/stats/risk-summary/").data
    assert data["flood"]["critical"] == 1
    assert data["hydroposts"] == 1


@pytest.mark.django_db
def test_level_timeseries_returns_daily_points(world):
    s = Structure.objects.create(
        type=world["hp"], name_ru="HP", condition_status="serviceable",
        geom=Point(71.0, 43.0, srid=4326), attributes={},
    )
    now = timezone.now()
    for i in range(90):
        HydropostReading.objects.create(
            structure=s, ts=now - datetime.timedelta(days=i),
            water_level=50 + i, danger_level=200, discharge=10, synthetic=True,
        )
    data = APIClient().get("/api/v1/stats/level-timeseries/", {"days": 90}).data
    assert 88 <= len(data) <= 91
    assert all("date" in p and "avg_level" in p for p in data)
