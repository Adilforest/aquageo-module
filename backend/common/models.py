"""Shared base models and mixins.

These are abstract, so they produce no migrations of their own. Concrete
models in catalog/accounts/etc. inherit from ``BaseModel``.
"""
import uuid

from django.db import models


class TimeStampedMixin(models.Model):
    """Adds self-managed ``created_at`` / ``updated_at`` timestamps."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDPrimaryKeyMixin(models.Model):
    """Uses a non-sequential UUID primary key."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class BaseModel(UUIDPrimaryKeyMixin, TimeStampedMixin):
    """Project-wide base: UUID pk + timestamps."""

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class AuditLog(models.Model):
    """Append-only audit trail (actor / action / entity / payload).

    Introduced here for edit logging (#12). Issue #29 extends coverage (more
    actions, signals) and exposes the journal via admin/API.
    """

    actor = models.CharField("Кто", max_length=255, blank=True)
    action = models.CharField("Действие", max_length=64)
    entity_type = models.CharField("Тип сущности", max_length=64, blank=True)
    entity_id = models.CharField("ID сущности", max_length=64, blank=True)
    payload = models.JSONField("Данные", default=dict, blank=True)
    created_at = models.DateTimeField("Когда", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Запись аудита"
        verbose_name_plural = "Журнал аудита"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} {self.entity_type}/{self.entity_id} by {self.actor}"
