"""Application (gov-flow) model — issue #25, M5 foundation.

The approval flow applies ONLY to creating new objects (kind=create) — and
later decommission. Editing existing structures is a direct PATCH (#12) and is
NOT wrapped here. Signature/PDF/publish arrive in #26/#27.
"""
from django.conf import settings
from django.db import models

from catalog.models import Structure
from common.models import BaseModel


class Application(BaseModel):
    class Kind(models.TextChoices):
        CREATE = "create", "Создание"
        UPDATE = "update", "Изменение"
        DECOMMISSION = "decommission", "Вывод из эксплуатации"

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        SUBMITTED = "submitted", "На согласовании"
        APPROVED = "approved", "Согласовано"
        REJECTED = "rejected", "Отклонено"

    structure = models.ForeignKey(
        Structure, verbose_name="Сооружение", on_delete=models.CASCADE,
        related_name="applications",
    )
    kind = models.CharField("Тип заявки", max_length=16, choices=Kind.choices, default=Kind.CREATE)
    status = models.CharField(
        "Статус", max_length=12, choices=Status.choices, default=Status.DRAFT
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Заявитель", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="submitted_applications",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Согласующий", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="reviewed_applications",
    )
    submitted_at = models.DateTimeField("Подана", null=True, blank=True)
    decided_at = models.DateTimeField("Решение принято", null=True, blank=True)
    comment = models.TextField("Комментарий", blank=True)

    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} {self.structure_id} [{self.status}]"
