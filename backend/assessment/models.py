from django.db import models

from catalog.models import ConditionStatus, Structure
from common.models import BaseModel


class RepairStatus(models.TextChoices):
    NORM = "norm", "Норма"
    INSPECT = "inspect", "Требуется осмотр"
    REPAIR = "repair", "Требуется ремонт"
    CRITICAL = "critical", "Критическое"


class ConditionAssessment(BaseModel):
    """Computed condition/repair status with an explainable breakdown.

    ``risk_scores`` holds the factor-by-factor breakdown (see services.py).
    ``next_inspection_due`` is filled by the inspection-interval model (#17).
    """

    structure = models.ForeignKey(
        Structure,
        verbose_name="Сооружение",
        on_delete=models.CASCADE,
        related_name="assessments",
    )
    assessed_at = models.DateTimeField("Дата оценки")
    condition_status = models.CharField(
        "Тех. состояние", max_length=12, choices=ConditionStatus.choices
    )
    repair_status = models.CharField(
        "Статус ремонта", max_length=12, choices=RepairStatus.choices
    )
    next_inspection_due = models.DateField("Следующий осмотр", null=True, blank=True)
    risk_scores = models.JSONField("Разбор/риски", default=dict, blank=True)
    model_version = models.CharField("Версия модели", max_length=32, blank=True)

    class Meta:
        verbose_name = "Оценка состояния"
        verbose_name_plural = "Оценки состояния"
        ordering = ["-assessed_at"]

    def __str__(self) -> str:
        return f"{self.structure_id}: {self.condition_status}/{self.repair_status}"
