"""Object card: detail retrieve + PATCH edit, RBAC, audit, validation (PostGIS)."""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient

from accounts.models import Role
from catalog.models import Inspection, ObjectType, Structure
from common.models import AuditLog

User = get_user_model()

CANAL_SCHEMA = {
    "type": "object",
    "properties": {"length_km": {"type": "number"}, "material": {"type": "string"}},
    "required": ["length_km"],
}


@pytest.fixture
def canal_type(db):
    return ObjectType.objects.create(
        code="canal", name_ru="Канал", geometry_kind="line", schema=CANAL_SCHEMA
    )


@pytest.fixture
def structure(canal_type):
    s = Structure.objects.create(
        type=canal_type, name_ru="Канал Тест", geom=Point(71.0, 43.0, srid=4326),
        condition_status="repair", commissioning_year=1980,
        attributes={"length_km": 12, "material": "earth"},
    )
    Inspection.objects.create(structure=s, inspected_at="2025-06-01", inspector="И1")
    return s


def client_for(role):
    User.objects.create_user("u", password="p", role=role)
    c = APIClient()
    token = APIClient().post(
        "/api/v1/auth/login/", {"username": "u", "password": "p"}, format="json"
    ).data["access"]
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return c


def url(s):
    return f"/api/v1/structures/{s.pk}/"


@pytest.mark.django_db
def test_detail_includes_schema_inspections_attachments(structure):
    resp = APIClient().get(url(structure))
    assert resp.status_code == 200
    assert resp.data["type_detail"]["schema"]["required"] == ["length_km"]
    assert len(resp.data["inspections"]) == 1
    assert resp.data["attributes"]["length_km"] == 12


@pytest.mark.django_db
def test_engineer_patches_common_field_and_writes_audit(structure):
    client = client_for(Role.ENGINEER)
    resp = client.patch(url(structure), {"responsible_org": "Казводхоз"}, format="json")
    assert resp.status_code == 200
    structure.refresh_from_db()
    assert structure.responsible_org == "Казводхоз"
    log = AuditLog.objects.filter(entity_id=str(structure.pk), action="update").latest("created_at")
    assert "responsible_org" in log.payload["changed"]


@pytest.mark.django_db
def test_engineer_patches_attributes(structure):
    client = client_for(Role.ENGINEER)
    resp = client.patch(
        url(structure), {"attributes": {"length_km": 99, "material": "concrete"}}, format="json"
    )
    assert resp.status_code == 200
    structure.refresh_from_db()
    assert structure.attributes["length_km"] == 99
    assert AuditLog.objects.filter(entity_id=str(structure.pk)).exists()


@pytest.mark.django_db
def test_viewer_cannot_patch(structure):
    client = client_for(Role.VIEWER)
    resp = client.patch(url(structure), {"responsible_org": "X"}, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_invalid_attributes_rejected(structure):
    client = client_for(Role.ENGINEER)
    # length_km must be a number
    resp = client.patch(url(structure), {"attributes": {"length_km": "много"}}, format="json")
    assert resp.status_code == 400
    assert "attributes" in resp.data


@pytest.mark.django_db
def test_condition_status_is_not_editable(structure):
    client = client_for(Role.ENGINEER)
    resp = client.patch(url(structure), {"condition_status": "serviceable"}, format="json")
    assert resp.status_code == 200
    structure.refresh_from_db()
    assert structure.condition_status == "repair"  # unchanged (read-only)
