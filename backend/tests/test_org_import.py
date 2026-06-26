"""Organizers' dataset import tests (issue #65), synthetic rows (PostGIS)."""
import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from catalog.models import Structure
from catalog.org_import import import_rows, parse_row


def row(n, wear=0.3, district="Район 1"):
    r = [""] * 22
    r[0] = float(n)
    r[1] = 1973.0
    r[2] = "р. Иртыш"
    r[3] = 3.0          # capacity_m3s
    r[4] = 7.74         # length_km
    r[6] = 7.74         # length_lined_km
    r[14] = 0.85        # efficiency_design
    r[15] = 0.73        # efficiency_actual
    r[16] = district    # served_districts
    r[17] = "Сельский округ 1"
    r[18] = wear        # износ (fraction)
    r[19] = "удов."     # reported_condition
    r[20] = "Кадастровый № 0001"
    return r


@pytest.fixture
def seeded(db):
    call_command("seed_reference")


@pytest.mark.django_db
def test_parse_row_maps_fields_and_normalizes_wear():
    f = parse_row(row(5, wear=0.3), 12)
    assert f["source_key"] == "org-xls:canal:12"  # unique by absolute row index
    assert f["attributes"]["dataset_no"] == 5
    assert f["wear_percent"] == 30  # 0.3 -> 30%
    assert f["attributes"]["water_source"] == "р. Иртыш"
    assert f["attributes"]["capacity_m3s"] == 3.0
    assert f["attributes"]["served_districts"] == "Район 1"
    assert "#5" in f["name_ru"] and "Район 1" in f["name_ru"]


@pytest.mark.django_db
def test_group_header_row_is_skipped():
    grp = [""] * 22
    grp[0] = "Группа объектов 2"
    assert parse_row(grp, 9) is None


@pytest.mark.django_db
def test_import_creates_canals_without_geom(seeded):
    created, skipped = import_rows([row(1), row(2), row(3)])
    assert (created, skipped) == (3, 0)
    canals = Structure.objects.filter(type__code="canal", needs_geocoding=True)
    assert canals.count() == 3
    assert all(c.geom is None for c in canals)


@pytest.mark.django_db
def test_wear_fraction_becomes_percent(seeded):
    import_rows([row(1, wear=0.3)])  # row_offset=7 -> source_key ...:7
    s = Structure.objects.get(attributes__source_key="org-xls:canal:7")
    assert float(s.wear_percent) == 30.0


@pytest.mark.django_db
def test_duplicate_dataset_numbers_are_kept_distinct(seeded):
    # № restarts per group; two rows with the same № must both import.
    created, _ = import_rows([row(1), row(1)])
    assert created == 2
    assert Structure.objects.filter(needs_geocoding=True).count() == 2


@pytest.mark.django_db
def test_in_catalog_but_not_in_geojson(seeded):
    import_rows([row(1), row(2), row(3)])
    api = APIClient()
    listed = api.get("/api/v1/structures/", {"needs_geocoding": "true"})
    assert listed.data["count"] == 3
    geo = api.get("/api/v1/structures/geojson/")
    assert len(geo.data["features"]) == 0  # no geometry -> not on the map


@pytest.mark.django_db
def test_import_is_idempotent(seeded):
    import_rows([row(1), row(2)])
    created, skipped = import_rows([row(1), row(2)])
    assert (created, skipped) == (0, 2)
    assert Structure.objects.filter(needs_geocoding=True).count() == 2


@pytest.mark.django_db
def test_attributes_pass_canal_schema(seeded):
    # import_rows calls full_clean -> jsonschema validation; success means valid.
    import_rows([row(1)])
    s = Structure.objects.get(attributes__source_key="org-xls:canal:7")
    assert s.attributes["efficiency_design"] == 0.85
    assert s.attributes["reported_condition"] == "удов."
