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
