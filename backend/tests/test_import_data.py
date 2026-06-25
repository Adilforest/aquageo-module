"""Importer tests using small synthetic fixtures (mapping logic).

The "hundreds of objects" acceptance is verified separately against the real
data files in Docker; here we assert the mapping rules deterministically.
"""
import json
import zipfile

import pytest
from django.core.management import call_command

from catalog.models import Inspection, Structure, WaterBody

HYDROPOSTS_CSV = (
    "id,code,name,bassein,region,longitude,latitude,danger_level,level_mean,water_temp,date\n"
    "1,1001,Пост1,Шу-Талас,Жамбылская область,71.0,43.0,low,120,15,2026-01-01\n"
    "2,1002,Пост2,Иртыш,Абайская область,80.0,50.0,no_data,200,12,2026-01-01\n"
)


def _feature(geom_type, coords, props):
    return {
        "type": "Feature",
        "properties": props,
        "geometry": {"type": geom_type, "coordinates": coords},
    }


def _write_geojson_zip(path, features):
    member = "data.geojson"
    payload = json.dumps({"type": "FeatureCollection", "features": features})
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(member, payload)


@pytest.fixture
def fixtures(tmp_path):
    hp = tmp_path / "hp.csv"
    hp.write_text(HYDROPOSTS_CSV, encoding="utf-8-sig")

    overpass = tmp_path / "overpass.geojson"
    overpass.write_text(json.dumps({"type": "FeatureCollection", "features": [
        _feature("Point", [71.0, 43.0], {"@id": "node/1", "waterway": "dam", "name": "Плотина1"}),
        _feature("Point", [71.1, 43.1], {"@id": "node/2", "waterway": "weir", "name": "Сброс1"}),
        _feature("Point", [71.2, 43.2], {"@id": "node/3", "man_made": "dyke", "name": "Дамба1"}),
        _feature("Point", [60.0, 40.0], {"@id": "node/4", "waterway": "dam", "name": "Вне"}),
        _feature("Point", [71.3, 43.3], {"@id": "node/5", "waterway": "river", "name": "НеТочка"}),
    ]}))

    lines = tmp_path / "lines.zip"
    _write_geojson_zip(lines, [
        _feature("LineString", [[71.0, 43.0], [71.1, 43.1]],
                 {"waterway": "canal", "name": "Канал1", "osm_id": 101}),
        _feature("LineString", [[60.0, 40.0], [60.1, 40.1]],
                 {"waterway": "canal", "name": "КаналВне", "osm_id": 102}),
        _feature("LineString", [[71.2, 43.2], [71.3, 43.3]],
                 {"waterway": "river", "name:ru": "Тестречка", "osm_id": 103}),
        _feature("LineString", [[71.2, 43.2], [71.3, 43.3]],
                 {"waterway": "river", "name": None, "osm_id": 104}),
        _feature("LineString", [[71.2, 43.2], [71.25, 43.25]],
                 {"waterway": "ditch", "name": "Канава", "osm_id": 105}),
    ])

    polygons = tmp_path / "polygons.zip"
    ring = [[[71.0, 43.0], [71.0, 43.1], [71.1, 43.1], [71.1, 43.0], [71.0, 43.0]]]
    _write_geojson_zip(polygons, [
        _feature("Polygon", ring, {"natural": "water", "water": "reservoir",
                                    "name:ru": "Тестводохр", "osm_id": 201}),
        _feature("Polygon", ring, {"natural": "water", "water": "pond",
                                    "name": "Прудик", "osm_id": 202}),
    ])
    return {
        "hydroposts": str(hp), "overpass": str(overpass),
        "lines": str(lines), "polygons": str(polygons),
    }


def _run(fx):
    call_command("seed_reference")
    call_command(
        "import_data",
        hydroposts=fx["hydroposts"], overpass=fx["overpass"],
        lines=fx["lines"], polygons=fx["polygons"],
    )


@pytest.mark.django_db
def test_hydroposts_become_structures_with_basin_mapping(fixtures):
    _run(fixtures)
    posts = Structure.objects.filter(type__code="hydropost")
    assert posts.count() == 2
    p1 = posts.get(name_ru="Пост1")
    assert p1.geom.geom_type == "Point"
    assert p1.basin.name_ru == "Шу-Таласский"
    assert p1.admin_unit.kato == "31"
    assert posts.get(name_ru="Пост2").admin_unit is None  # non-Jambyl region


@pytest.mark.django_db
def test_overpass_points_mapped_by_tag_and_bbox(fixtures):
    _run(fixtures)
    assert Structure.objects.filter(type__code="dam", name_ru="Плотина1").exists()
    assert Structure.objects.filter(type__code="spillway", name_ru="Сброс1").exists()
    assert Structure.objects.filter(type__code="dike", name_ru="Дамба1").exists()
    # Out-of-bbox dam skipped; river point is not a point-structure tag.
    assert not Structure.objects.filter(name_ru="Вне").exists()
    assert not Structure.objects.filter(name_ru="НеТочка").exists()


@pytest.mark.django_db
def test_lines_canal_is_structure_river_is_waterbody(fixtures):
    _run(fixtures)
    canal = Structure.objects.get(type__code="canal", name_ru="Канал1")
    assert canal.geom.geom_type == "LineString"
    # Out-of-bbox canal and ditches are not imported.
    assert not Structure.objects.filter(name_ru="КаналВне").exists()
    assert not Structure.objects.filter(name_ru="Канава").exists()
    # Named river -> WaterBody, not Structure; unnamed river skipped.
    assert WaterBody.objects.filter(name_ru="Тестречка", kind="river").exists()
    assert not Structure.objects.filter(name_ru="Тестречка").exists()


@pytest.mark.django_db
def test_polygons_reservoir_is_waterbody(fixtures):
    _run(fixtures)
    wb = WaterBody.objects.get(name_ru="Тестводохр")
    assert wb.kind == "reservoir"
    assert wb.geom.geom_type == "Polygon"
    assert not WaterBody.objects.filter(name_ru="Прудик").exists()  # pond skipped


@pytest.mark.django_db
def test_imported_structures_get_plausible_condition_and_inspection(fixtures):
    _run(fixtures)
    for s in Structure.objects.all():
        assert s.condition_status in {"serviceable", "monitoring", "repair", "emergency"}
        assert s.wear_percent is not None
        assert s.commissioning_year is not None
        assert s.inspections.count() == 1


@pytest.mark.django_db
def test_import_is_idempotent(fixtures):
    _run(fixtures)
    counts = (Structure.objects.count(), WaterBody.objects.count(), Inspection.objects.count())
    call_command(
        "import_data",
        hydroposts=fixtures["hydroposts"], overpass=fixtures["overpass"],
        lines=fixtures["lines"], polygons=fixtures["polygons"],
    )
    again = (Structure.objects.count(), WaterBody.objects.count(), Inspection.objects.count())
    assert again == counts
