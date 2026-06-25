"""Catalog reference-model tests (require PostGIS; run in Docker/CI)."""
import pytest
from django.contrib.admin.sites import site
from django.contrib.gis.geos import LineString, MultiPolygon, Polygon

from catalog.models import AdminUnit, Basin, ObjectType, WaterBody

SQUARE = Polygon(((70.0, 43.0), (70.0, 44.0), (71.0, 44.0), (71.0, 43.0), (70.0, 43.0)))


@pytest.mark.django_db
def test_object_type_create():
    ot = ObjectType.objects.create(
        code="hydropost",
        name_ru="Гидропост",
        name_kk="Гидробекет",
        geometry_kind="point",
        schema={"type": "object", "properties": {"datum": {"type": "number"}}},
    )
    assert ObjectType.objects.get(pk="hydropost") == ot
    assert ot.schema["type"] == "object"


@pytest.mark.django_db
def test_admin_unit_self_hierarchy():
    region = AdminUnit.objects.create(kato="31", name_ru="Жамбылская область", level="region")
    district = AdminUnit.objects.create(
        kato="3110", name_ru="Кордайский район", level="district", parent=region
    )
    okrug = AdminUnit.objects.create(
        kato="311010", name_ru="Кордайский с.о.", level="okrug", parent=district
    )
    assert okrug.parent.parent == region
    assert list(region.children.all()) == [district]


@pytest.mark.django_db
def test_basin_with_polygon_geometry():
    basin = Basin.objects.create(
        name_ru="Шу-Таласский", geom=MultiPolygon(SQUARE, srid=4326)
    )
    fetched = Basin.objects.get(pk=basin.pk)
    assert fetched.geom is not None
    assert fetched.geom.srid == 4326
    assert fetched.geom.geom_type == "MultiPolygon"


@pytest.mark.django_db
def test_water_body_links_basin_and_stores_line_geometry():
    basin = Basin.objects.create(name_ru="Шу-Таласский")
    river = WaterBody.objects.create(
        name_ru="Талас",
        name_kk="Талас",
        kind=WaterBody.Kind.RIVER,
        basin=basin,
        geom=LineString((70.1, 43.1), (70.5, 43.4), srid=4326),
    )
    fetched = WaterBody.objects.get(pk=river.pk)
    assert fetched.basin == basin
    assert fetched.geom.geom_type == "LineString"
    assert list(basin.water_bodies.all()) == [river]


@pytest.mark.django_db
def test_reference_models_registered_in_admin():
    for model in (ObjectType, AdminUnit, Basin, WaterBody):
        assert model in site._registry
