"""Catalog reference models (CLAUDE.md §5).

Geometry uses GeoDjango (PostGIS) — enabled from this issue onward. ``Structure``
itself and its attachments/inspections arrive in issue #6.
"""
import jsonschema
from django.conf import settings
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError

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


class ConditionStatus(models.TextChoices):
    SERVICEABLE = "serviceable", "Исправное"
    MONITORING = "monitoring", "Требует наблюдения"
    REPAIR = "repair", "Требует ремонта"
    EMERGENCY = "emergency", "Аварийное"


class LifecycleStatus(models.TextChoices):
    DRAFT = "draft", "Черновик"
    PENDING_REVIEW = "pending_review", "На согласовании"
    PUBLISHED = "published", "Опубликовано"
    DECOMMISSION_REQUESTED = "decommission_requested", "Запрошен вывод"
    ARCHIVED = "archived", "В архиве"


class Significance(models.TextChoices):
    REPUBLICAN = "republican", "Республиканское"
    REGIONAL = "regional", "Областное"
    DISTRICT = "district", "Районное"
    LOCAL = "local", "Местное"


class Structure(BaseModel):
    """A hydro structure of any type. Type-specific parameters live in the
    ``attributes`` JSONB field, validated against ``ObjectType.schema``.

    ``condition_status`` is computed by the assessment service (issue #16); the
    field stores the last computed value.
    """

    type = models.ForeignKey(
        ObjectType,
        verbose_name="Тип",
        on_delete=models.PROTECT,
        related_name="structures",
    )
    name_ru = models.CharField("Название (RU)", max_length=255)
    name_kk = models.CharField("Название (KK)", max_length=255, blank=True)
    name_en = models.CharField("Название (EN)", max_length=255, blank=True)
    geom = models.GeometryField("Геометрия", srid=4326, null=True, blank=True)

    water_body = models.ForeignKey(
        WaterBody,
        verbose_name="Водный объект",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="structures",
    )
    basin = models.ForeignKey(
        Basin,
        verbose_name="Бассейн",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="structures",
    )
    admin_unit = models.ForeignKey(
        AdminUnit,
        verbose_name="Админ. единица",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="structures",
    )

    commissioning_year = models.PositiveIntegerField("Год ввода", null=True, blank=True)
    wear_percent = models.DecimalField(
        "Износ, %", max_digits=5, decimal_places=2, null=True, blank=True
    )
    ownership = models.CharField("Форма собственности", max_length=128, blank=True)
    cadastral_number = models.CharField("Кадастровый номер", max_length=64, blank=True)
    state_act = models.CharField("Госакт", max_length=128, blank=True)
    responsible_org = models.CharField("Ответственная организация", max_length=255, blank=True)
    significance = models.CharField(
        "Значимость", max_length=12, choices=Significance.choices, blank=True
    )

    condition_status = models.CharField(
        "Тех. состояние (вычисляется)",
        max_length=12,
        choices=ConditionStatus.choices,
        blank=True,
    )
    status = models.CharField(
        "Статус жизненного цикла",
        max_length=24,
        choices=LifecycleStatus.choices,
        default=LifecycleStatus.DRAFT,
    )
    attributes = models.JSONField("Атрибуты (по схеме типа)", default=dict, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Создал",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_structures",
    )

    class Meta:
        verbose_name = "Сооружение"
        verbose_name_plural = "Сооружения"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["condition_status"]),
        ]

    def __str__(self) -> str:
        return self.name_ru

    def clean(self) -> None:
        """Validate ``attributes`` against the JSON schema of the object type."""
        super().clean()
        schema = getattr(self.type, "schema", None)
        if schema:
            try:
                jsonschema.validate(instance=self.attributes, schema=schema)
            except jsonschema.ValidationError as exc:
                raise ValidationError(
                    {"attributes": f"Не соответствует схеме типа: {exc.message}"}
                ) from exc
            except jsonschema.SchemaError as exc:
                raise ValidationError(
                    {"attributes": f"Некорректная JSON-схема типа: {exc.message}"}
                ) from exc


class Attachment(BaseModel):
    """A file attached to a structure (photo, passport, act, order, source)."""

    class Kind(models.TextChoices):
        PHOTO = "photo", "Фото"
        PASSPORT = "passport", "Паспорт"
        ACT = "act", "Акт"
        ORDER = "order", "Приказ"
        SOURCE_FILE = "source_file", "Исходный файл импорта"

    structure = models.ForeignKey(
        Structure,
        verbose_name="Сооружение",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    kind = models.CharField("Тип", max_length=16, choices=Kind.choices)
    file = models.FileField("Файл", upload_to="attachments/%Y/%m/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Загрузил",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_attachments",
    )

    class Meta:
        verbose_name = "Вложение"
        verbose_name_plural = "Вложения"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} #{self.pk}"


class Inspection(BaseModel):
    """A field inspection of a structure (feeds the assessment service)."""

    structure = models.ForeignKey(
        Structure,
        verbose_name="Сооружение",
        on_delete=models.CASCADE,
        related_name="inspections",
    )
    inspected_at = models.DateField("Дата осмотра")
    inspector = models.CharField("Инспектор", max_length=255, blank=True)
    condition_observed = models.CharField(
        "Наблюдаемое состояние",
        max_length=12,
        choices=ConditionStatus.choices,
        blank=True,
    )
    wear_percent = models.DecimalField(
        "Износ, %", max_digits=5, decimal_places=2, null=True, blank=True
    )
    notes = models.TextField("Примечания", blank=True)

    class Meta:
        verbose_name = "Осмотр"
        verbose_name_plural = "Осмотры"
        ordering = ["-inspected_at"]

    def __str__(self) -> str:
        return f"Осмотр {self.structure_id} @ {self.inspected_at}"
