"""ParseJob — AI document parsing (issue #22, M4).

A ParseJob ingests an Excel/PDF document, extracts fields via the LLM adapter
(#21), and produces a DRAFT Structure. ``match_status`` / ``matched_structure``
are filled by the DB comparison step (#23), not here.
"""
from django.conf import settings
from django.db import models

from catalog.models import Structure
from common.models import BaseModel


class ParseJob(BaseModel):
    class SourceKind(models.TextChoices):
        EXCEL = "excel", "Excel"
        PDF = "pdf", "PDF"
        MANUAL = "manual", "Вручную"

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        PROCESSING = "processing", "Обработка"
        DONE = "done", "Готово"
        ERROR = "error", "Ошибка"

    class MatchStatus(models.TextChoices):
        EXISTING = "existing", "Существующий"
        NEW = "new", "Новый"
        NEEDS_CHECK = "needs_check", "Требует проверки"

    source_kind = models.CharField("Источник", max_length=10, choices=SourceKind.choices)
    file = models.FileField("Файл", upload_to="parse_jobs/%Y/%m/", null=True, blank=True)
    status = models.CharField(
        "Статус", max_length=12, choices=Status.choices, default=Status.PENDING
    )
    raw_extract = models.JSONField("Извлечённые поля", default=dict, blank=True)
    confidence = models.JSONField("Уверенность по полям", default=dict, blank=True)
    error_message = models.TextField("Ошибка", blank=True)

    # Filled when the draft is created (here) and by the comparison step (#23).
    result_structure = models.ForeignKey(
        Structure, verbose_name="Черновик-результат", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="origin_parse_jobs",
    )
    match_status = models.CharField(
        "Статус сверки", max_length=12, choices=MatchStatus.choices, blank=True
    )
    matched_structure = models.ForeignKey(
        Structure, verbose_name="Совпавший объект", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="matched_parse_jobs",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Создал", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="parse_jobs",
    )

    class Meta:
        verbose_name = "Задача парсинга"
        verbose_name_plural = "Задачи парсинга"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"ParseJob {self.pk} [{self.source_kind}/{self.status}]"
