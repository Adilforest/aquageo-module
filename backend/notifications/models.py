"""In-app notifications (issue #28).

A ``Notification`` is one message for one recipient, raised in reaction to an
existing domain event (application submitted/decided, risk alert). It is never
created by hand via the API — only the event subscriber (``signals.py``) writes
rows. ``related_entity_*`` is a lightweight generic pointer (type + id) so the
frontend can deep-link to the source object without a hard FK per entity type.
"""
from django.conf import settings
from django.db import models

from common.models import BaseModel


class Notification(BaseModel):
    class Kind(models.TextChoices):
        APPLICATION_SUBMITTED = "application_submitted", "Заявка подана"
        APPLICATION_APPROVED = "application_approved", "Заявка согласована"
        APPLICATION_REJECTED = "application_rejected", "Заявка отклонена"
        RISK_ALERT = "risk_alert", "Риск-оповещение"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Получатель",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField("Тип", max_length=32, choices=Kind.choices)
    message = models.TextField("Сообщение")
    related_entity_type = models.CharField("Тип сущности", max_length=64, blank=True)
    related_entity_id = models.CharField("ID сущности", max_length=64, blank=True)
    read = models.BooleanField("Прочитано", default=False, db_index=True)

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "read"])]

    def __str__(self) -> str:
        state = "read" if self.read else "new"
        return f"{self.get_kind_display()} -> {self.recipient_id} [{state}]"
