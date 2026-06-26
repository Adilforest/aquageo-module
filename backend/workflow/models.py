"""Application (gov-flow) model — issue #25, M5 foundation.

The approval flow applies ONLY to creating new objects (kind=create) — and
later decommission. Editing existing structures is a direct PATCH (#12) and is
NOT wrapped here. Approving a create application produces a stub Signature (#26)
and a generated ApprovalOrder PDF (#27), then publishes the structure.
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


class Signature(BaseModel):
    """Stub digital signature (#26).

    Imitates an ECP/NCALayer signature WITHOUT any real crypto: ``valid`` is
    always true and ``cert_subject`` is a fabricated demo subject. It marks who
    approved an application and when, so the gov-flow can show a "signed" state.
    """

    application = models.ForeignKey(
        Application, verbose_name="Заявка", on_delete=models.CASCADE,
        related_name="signatures",
    )
    signer = models.CharField("Подписант", max_length=255, blank=True)
    signed_at = models.DateTimeField("Подписано")
    cert_subject = models.CharField("Субъект сертификата", max_length=512, blank=True)
    cms_blob = models.TextField("CMS (заглушка)", blank=True)
    valid = models.BooleanField("Подпись валидна", default=True)

    class Meta:
        verbose_name = "Подпись (ЭЦП-заглушка)"
        verbose_name_plural = "Подписи (ЭЦП-заглушка)"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Подпись {self.signer} для {self.application_id} [{self.valid}]"


class ApprovalOrder(BaseModel):
    """Generated approval order (приказ) PDF for an approved application (#27)."""

    application = models.ForeignKey(
        Application, verbose_name="Заявка", on_delete=models.CASCADE,
        related_name="orders",
    )
    number = models.CharField("Номер приказа", max_length=64)
    file = models.FileField("Файл приказа (PDF)", upload_to="orders/%Y/%m/")
    issued_at = models.DateTimeField("Издан")

    class Meta:
        verbose_name = "Приказ о согласовании"
        verbose_name_plural = "Приказы о согласовании"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Приказ {self.number} ({self.application_id})"
