"""Catalog reference models (CLAUDE.md §5).

Geometry uses GeoDjango (PostGIS) — enabled from this issue onward. ``Structure``
itself and its attachments/inspections arrive in issue #6.
"""
from django.contrib.gis.db import models

from common.models import BaseModel


class GeometryKind(models.TextChoices):
    POINT = "point", "Точка"
    LINE = "line", "Линия"
    POLYGON = "polygon", "Полигон"


class ObjectType(models.Model):
    """A type of hydro structure; ``schema`` validates Structure.attributes."""

    code = models.CharField("Код", max_length=32, primary_key=True)
    name_ru = models.CharField("Название (RU)", max_length=128)
    name_kk = models.CharField("Название (KK)", max_length=128, blank=True)
    name_en = models.CharField("Название (EN)", max_length=128, blank=True)
    schema = models.JSONField("JSON-схема атрибутов", default=dict, blank=True)
    geometry_kind = models.CharField(
        "Тип геометрии", max_length=8, choices=GeometryKind.choices
    )

    class Meta:
        verbose_name = "Тип объекта"
        verbose_name_plural = "Типы объектов"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.name_ru} ({self.code})"


class Basin(BaseModel):
    """Water management basin (ВХБ). Eight in Kazakhstan."""

    name_ru = models.CharField("Название (RU)", max_length=128)
    name_kk = models.CharField("Название (KK)", max_length=128, blank=True)
    name_en = models.CharField("Название (EN)", max_length=128, blank=True)
    geom = models.MultiPolygonField("Геометрия", srid=4326, null=True, blank=True)

    class Meta:
        verbose_name = "Бассейн"
        verbose_name_plural = "Бассейны"
        ordering = ["name_ru"]

    def __str__(self) -> str:
        return self.name_ru


class AdminUnit(models.Model):
    """Administrative unit (КАТО), self-referential: region → district → okrug.

    This hierarchy is the scaling mechanism across regions (new rows, not a new
    system).
    """

    class Level(models.TextChoices):
        REGION = "region", "Область"
        DISTRICT = "district", "Район"
        OKRUG = "okrug", "Округ"

    kato = models.CharField("КАТО", max_length=20, primary_key=True)
    name_ru = models.CharField("Название (RU)", max_length=128)
    name_kk = models.CharField("Название (KK)", max_length=128, blank=True)
    name_en = models.CharField("Название (EN)", max_length=128, blank=True)
    level = models.CharField("Уровень", max_length=10, choices=Level.choices)
    parent = models.ForeignKey(
        "self",
        verbose_name="Родитель",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )

    class Meta:
        verbose_name = "Админ. единица"
        verbose_name_plural = "Админ. единицы (КАТО)"
        ordering = ["kato"]

    def __str__(self) -> str:
        return f"{self.name_ru} [{self.get_level_display()}]"


class WaterBody(BaseModel):
    """Natural water object: river, stream, lake, reservoir.

    Distinct from canals/ditches, which are Structures (see DATA_NOTES.md).
    Geometry is generic (LineString for rivers, Polygon for reservoirs).
    """

    class Kind(models.TextChoices):
        RIVER = "river", "Река"
        STREAM = "stream", "Ручей"
        LAKE = "lake", "Озеро"
        RESERVOIR = "reservoir", "Водохранилище"
        OTHER = "other", "Другое"

    name_ru = models.CharField("Название (RU)", max_length=200)
    name_kk = models.CharField("Название (KK)", max_length=200, blank=True)
    name_en = models.CharField("Название (EN)", max_length=200, blank=True)
    kind = models.CharField(
        "Тип", max_length=12, choices=Kind.choices, default=Kind.RIVER
    )
    basin = models.ForeignKey(
        Basin,
        verbose_name="Бассейн",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="water_bodies",
    )
    geom = models.GeometryField("Геометрия", srid=4326, null=True, blank=True)

    class Meta:
        verbose_name = "Водный объект"
        verbose_name_plural = "Водные объекты"
        ordering = ["name_ru"]

    def __str__(self) -> str:
        return self.name_ru
