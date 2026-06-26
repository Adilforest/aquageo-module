from django.db import models

from catalog.models import Structure


class HydropostReading(models.Model):
    """A single hydropost measurement (time series). CLAUDE.md §5.

    ``synthetic=True`` marks generated demo history; the real source measurement
    is stored as a single ``synthetic=False`` anchor point.
    """

    structure = models.ForeignKey(
        Structure,
        verbose_name="Гидропост",
        on_delete=models.CASCADE,
        related_name="readings",
    )
    ts = models.DateTimeField("Момент")
    water_level = models.FloatField("Уровень", null=True, blank=True)
    danger_level = models.FloatField("Опасный уровень", null=True, blank=True)
    discharge = models.FloatField("Расход", null=True, blank=True)
    water_temp = models.FloatField("Температура воды", null=True, blank=True)
    status_code = models.CharField("Код состояния", max_length=32, blank=True)
    synthetic = models.BooleanField("Синтетическая точка", default=False)

    class Meta:
        verbose_name = "Замер гидропоста"
        verbose_name_plural = "Замеры гидропостов"
        ordering = ["ts"]
        indexes = [models.Index(fields=["structure", "ts"])]

    def __str__(self) -> str:
        return f"{self.structure_id} @ {self.ts:%Y-%m-%d}: {self.water_level}"
