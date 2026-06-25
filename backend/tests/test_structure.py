"""Structure / Attachment / Inspection tests (require PostGIS)."""
import datetime

import pytest
from django.contrib.admin.sites import site
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError

from catalog.models import (
    Attachment,
    ConditionStatus,
    Inspection,
    ObjectType,
    Structure,
)

CANAL_SCHEMA = {
    "type": "object",
    "properties": {
        "length_m": {"type": "number"},
        "material": {"type": "string"},
    },
    "required": ["length_m"],
}


@pytest.fixture
def canal_type(db):
    return ObjectType.objects.create(
        code="canal", name_ru="Канал", geometry_kind="line", schema=CANAL_SCHEMA
    )


@pytest.fixture
def typeless(db):
    return ObjectType.objects.create(
        code="pond", name_ru="Пруд", geometry_kind="polygon", schema={}
    )


@pytest.mark.django_db
def test_structure_valid_attributes_pass_schema(canal_type):
    s = Structure(
        type=canal_type,
        name_ru="Магистральный канал",
        geom=Point(71.0, 43.0, srid=4326),
        attributes={"length_m": 1200, "material": "concrete"},
    )
    s.full_clean()  # must not raise
    s.save()
    assert Structure.objects.get(pk=s.pk).attributes["length_m"] == 1200


@pytest.mark.django_db
def test_structure_invalid_attributes_rejected(canal_type):
    # Missing required "length_m".
    s = Structure(type=canal_type, name_ru="Без длины", attributes={"material": "earth"})
    with pytest.raises(ValidationError) as exc:
        s.full_clean()
    assert "attributes" in exc.value.message_dict


@pytest.mark.django_db
def test_structure_wrong_type_value_rejected(canal_type):
    s = Structure(
        type=canal_type, name_ru="Кривой тип", attributes={"length_m": "много"}
    )
    with pytest.raises(ValidationError):
        s.full_clean()


@pytest.mark.django_db
def test_structure_empty_schema_accepts_any_attributes(typeless):
    s = Structure(type=typeless, name_ru="Пруд 1", attributes={"anything": [1, 2, 3]})
    s.full_clean()  # empty schema -> no constraints


@pytest.mark.django_db
def test_structure_defaults_and_geometry(canal_type):
    s = Structure.objects.create(
        type=canal_type, name_ru="Канал 2", geom=Point(70.5, 43.5, srid=4326),
        attributes={"length_m": 10},
    )
    fetched = Structure.objects.get(pk=s.pk)
    assert fetched.status == "draft"
    assert fetched.geom.geom_type == "Point"


@pytest.mark.django_db
def test_attachment_and_inspection_relations(canal_type):
    s = Structure.objects.create(
        type=canal_type, name_ru="Канал 3", attributes={"length_m": 5}
    )
    att = Attachment.objects.create(structure=s, kind=Attachment.Kind.PHOTO, file="x.jpg")
    insp = Inspection.objects.create(
        structure=s,
        inspected_at=datetime.date(2025, 6, 1),
        condition_observed=ConditionStatus.MONITORING,
        wear_percent=42,
    )
    assert list(s.attachments.all()) == [att]
    assert list(s.inspections.all()) == [insp]


@pytest.mark.django_db
def test_structure_models_registered_in_admin():
    for model in (Structure, Attachment, Inspection):
        assert model in site._registry
