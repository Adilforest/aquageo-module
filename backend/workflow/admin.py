from django.contrib import admin

from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("kind", "structure", "status", "submitted_by", "reviewer", "decided_at")
    list_filter = ("status", "kind")
    search_fields = ("structure__name_ru",)
    readonly_fields = ("submitted_at", "decided_at", "created_at", "updated_at")
