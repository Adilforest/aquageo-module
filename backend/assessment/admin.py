from django.contrib import admin

from .models import ConditionAssessment


@admin.register(ConditionAssessment)
class ConditionAssessmentAdmin(admin.ModelAdmin):
    list_display = ("structure", "condition_status", "repair_status", "assessed_at")
    list_filter = ("condition_status", "repair_status")
    search_fields = ("structure__name_ru",)
    readonly_fields = ("assessed_at", "risk_scores", "model_version")
