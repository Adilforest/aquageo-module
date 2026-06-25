"""Tests for the /api/v1/structures API (require PostGIS)."""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient

from accounts.models import Role
from catalog.models import AdminUnit, Basin, ObjectType, Structure

User = get_user_model()
LIST_URL = "/api/v1/structures/"
GEOJSON_URL = "/api/v1/structures/geojson/"


@pytest.fixture
def reference(db):
    dam = ObjectType.objects.create(code="dam", name_ru="Плотина", geometry_kind="point")
    canal = ObjectType.objects.create(code="canal", name_ru="Канал", geometry_kind="line")
    basin_a = Basin.objects.create(name_ru="Шу-Таласский")
    basin_b = Basin.objects.create(name_ru="Иной")
    region = AdminUnit.objects.create(kato="31", name_ru="Жамбылская область", level="region")
    return {"dam": dam, "canal": canal, "basin_a": basin_a, "basin_b": basin_b, "region": region}


@pytest.fixture
def structures(reference):
    r = reference
    Structure.objects.create(
        type=r["dam"], name_ru="Плотина Альфа", geom=Point(71.0, 43.0, srid=4326),
        basin=r["basin_a"], admin_unit=r["region"], condition_status="emergency",
        attributes={},
    )
    Structure.objects.create(
        type=r["canal"], name_ru="Канал Бета", geom=Point(71.1, 43.1, srid=4326),
        basin=r["basin_a"], condition_status="serviceable", attributes={},
    )
    Structure.objects.create(
        type=r["dam"], name_ru="Плотина Гамма", geom=Point(72.0, 44.0, srid=4326),
        basin=r["basin_b"], condition_status="serviceable", attributes={},
    )
    return r


def engineer_client(db):
    User.objects.create_user("eng", password="p", role=Role.ENGINEER)
    c = APIClient()
    token = APIClient().post(
        "/api/v1/auth/login/", {"username": "eng", "password": "p"}, format="json"
    ).data["access"]
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return c


@pytest.mark.django_db
def test_list_is_paginated(structures):
    resp = APIClient().get(LIST_URL)
    assert resp.status_code == 200
    assert resp.data["count"] == 3
    assert "results" in resp.data


@pytest.mark.django_db
def test_filter_by_type(structures):
    resp = APIClient().get(LIST_URL, {"type": "dam"})
    assert resp.data["count"] == 2
    assert all(row["type"] == "dam" for row in resp.data["results"])


@pytest.mark.django_db
def test_filter_by_condition_and_basin(structures):
    by_cond = APIClient().get(LIST_URL, {"condition_status": "serviceable"})
    assert by_cond.data["count"] == 2
    by_basin = APIClient().get(LIST_URL, {"basin": str(structures["basin_b"].pk)})
    assert by_basin.data["count"] == 1


@pytest.mark.django_db
def test_search_by_name(structures):
    resp = APIClient().get(LIST_URL, {"search": "Гамма"})
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["name_ru"] == "Плотина Гамма"


@pytest.mark.django_db
def test_geojson_endpoint_returns_feature_collection(structures):
    resp = APIClient().get(GEOJSON_URL)
    assert resp.status_code == 200
    assert resp.data["type"] == "FeatureCollection"
    assert len(resp.data["features"]) == 3
    feat = resp.data["features"][0]
    assert feat["geometry"]["type"] == "Point"
    assert "condition_status" in feat["properties"]


@pytest.mark.django_db
def test_geojson_respects_filters(structures):
    resp = APIClient().get(GEOJSON_URL, {"type": "dam"})
    assert len(resp.data["features"]) == 2


@pytest.mark.django_db
def test_anonymous_cannot_create(reference):
    resp = APIClient().post(
        LIST_URL,
        {"type": "dam", "name_ru": "Новая", "geom": {"type": "Point", "coordinates": [71.0, 43.0]}},
        format="json",
    )
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_engineer_can_create_and_delete(reference, db):
    client = engineer_client(db)
    create = client.post(
        LIST_URL,
        {
            "type": "dam",
            "name_ru": "Новая плотина",
            "geom": {"type": "Point", "coordinates": [71.5, 43.5]},
            "attributes": {},
        },
        format="json",
    )
    assert create.status_code == 201, create.data
    sid = create.data["id"]
    assert Structure.objects.filter(pk=sid).exists()
    # created_by is recorded
    assert Structure.objects.get(pk=sid).created_by is not None

    detail = client.get(f"{LIST_URL}{sid}/")
    assert detail.status_code == 200
    assert detail.data["geom"]["type"] == "Point"

    assert client.delete(f"{LIST_URL}{sid}/").status_code == 204
    assert not Structure.objects.filter(pk=sid).exists()
