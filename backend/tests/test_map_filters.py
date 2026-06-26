"""Filter/search tests for the structures list and GeoJSON feed (PostGIS)."""
import pytest
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient

from catalog.models import AdminUnit, Basin, ObjectType, Structure

LIST_URL = "/api/v1/structures/"
GEOJSON_URL = "/api/v1/structures/geojson/"


@pytest.fixture
def world(db):
    dam = ObjectType.objects.create(code="dam", name_ru="Плотина", geometry_kind="point")
    dike = ObjectType.objects.create(code="dike", name_ru="Дамба", geometry_kind="point")
    canal = ObjectType.objects.create(code="canal", name_ru="Канал", geometry_kind="line")
    basin_a = Basin.objects.create(name_ru="Шу-Таласский")
    basin_b = Basin.objects.create(name_ru="Иной")
    region = AdminUnit.objects.create(kato="31", name_ru="Жамбылская область", level="region")
    d1 = AdminUnit.objects.create(
        kato="3110", name_ru="Байзакский", level="district", parent=region
    )
    d2 = AdminUnit.objects.create(
        kato="3114", name_ru="Жамбылский", level="district", parent=region
    )

    def mk(name, t, cond, basin, district):
        return Structure.objects.create(
            type=t, name_ru=name, geom=Point(71.0, 43.0, srid=4326),
            condition_status=cond, basin=basin, admin_unit=district, attributes={},
        )

    mk("Альфа", dam, "emergency", basin_a, d1)
    mk("Бета", dam, "repair", basin_a, d1)
    mk("Гамма", dike, "serviceable", basin_a, d2)
    mk("Дельта", canal, "monitoring", basin_b, d2)
    return {"basin_a": basin_a, "basin_b": basin_b, "region": region, "d1": d1, "d2": d2}


def count(params):
    return APIClient().get(LIST_URL, params).data["count"]


@pytest.mark.django_db
def test_filter_by_single_condition(world):
    assert count({"condition": "emergency"}) == 1


@pytest.mark.django_db
def test_filter_by_single_type(world):
    assert count({"type": "dam"}) == 2


@pytest.mark.django_db
def test_multi_condition_is_or(world):
    # repair OR emergency -> Альфа + Бета
    assert count({"condition": ["repair", "emergency"]}) == 2


@pytest.mark.django_db
def test_multi_type_is_or(world):
    # dam OR dike -> Альфа, Бета, Гамма
    assert count({"type": ["dam", "dike"]}) == 3


@pytest.mark.django_db
def test_combined_type_and_condition(world):
    # (dam OR dike) AND emergency -> Альфа only
    assert count({"type": ["dam", "dike"], "condition": ["emergency"]}) == 1


@pytest.mark.django_db
def test_filter_by_basin(world):
    assert count({"basin": str(world["basin_b"].pk)}) == 1


@pytest.mark.django_db
def test_filter_by_district(world):
    assert count({"district": "3114"}) == 2  # Гамма + Дельта


@pytest.mark.django_db
def test_search_by_name(world):
    assert count({"search": "Гамма"}) == 1


@pytest.mark.django_db
def test_geojson_matches_list_for_same_filters(world):
    params = {"type": ["dam", "dike"], "condition": ["repair", "emergency", "serviceable"]}
    list_count = APIClient().get(LIST_URL, params).data["count"]
    geo = APIClient().get(GEOJSON_URL, params).data
    assert geo["type"] == "FeatureCollection"
    assert len(geo["features"]) == list_count == 3


@pytest.mark.django_db
def test_basins_and_districts_endpoints(world):
    basins = APIClient().get("/api/v1/basins/").data
    assert {b["name_ru"] for b in basins} >= {"Шу-Таласский", "Иной"}
    districts = APIClient().get("/api/v1/admin-units/", {"level": "district"}).data
    katos = {d["kato"] for d in districts}
    assert katos == {"3110", "3114"}  # region excluded by level filter
