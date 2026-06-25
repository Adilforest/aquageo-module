"""Tests for the seed_reference management command (require DB)."""
import pytest
from django.core.management import call_command

from catalog.models import AdminUnit, Basin, ObjectType, WaterBody


@pytest.mark.django_db
def test_seed_populates_reference_data():
    call_command("seed_reference")

    # Object types: all 11 from CLAUDE.md §5, with schemas.
    assert ObjectType.objects.count() == 11
    canal = ObjectType.objects.get(pk="canal")
    assert canal.geometry_kind == "line"
    assert canal.schema["properties"]["length_km"]["type"] == "number"

    # Eight basins, Shu-Talas present.
    assert Basin.objects.count() == 8
    assert Basin.objects.filter(name_ru="Шу-Таласский").exists()

    # KATO hierarchy: region + districts + okrugs.
    region = AdminUnit.objects.get(kato="31")
    assert region.level == AdminUnit.Level.REGION
    assert region.children.filter(level=AdminUnit.Level.DISTRICT).count() >= 10
    okrug = AdminUnit.objects.get(kato="312201")
    assert okrug.level == AdminUnit.Level.OKRUG
    assert okrug.parent.parent == region

    # Rivers of the Shu-Talas basin.
    shu_talas = Basin.objects.get(name_ru="Шу-Таласский")
    for name in ("Талас", "Шу", "Аса"):
        river = WaterBody.objects.get(name_ru=name, kind=WaterBody.Kind.RIVER)
        assert river.basin == shu_talas


@pytest.mark.django_db
def test_seed_is_idempotent():
    call_command("seed_reference")
    counts = (
        ObjectType.objects.count(),
        Basin.objects.count(),
        AdminUnit.objects.count(),
        WaterBody.objects.count(),
    )
    call_command("seed_reference")
    counts_again = (
        ObjectType.objects.count(),
        Basin.objects.count(),
        AdminUnit.objects.count(),
        WaterBody.objects.count(),
    )
    assert counts == counts_again
