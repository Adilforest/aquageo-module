from django.contrib import admin

from .models import ParseJob


@admin.register(ParseJob)
class ParseJobAdmin(admin.ModelAdmin):
    list_display = ("id", "source_kind", "status", "match_status", "result_structure", "created_at")
    list_filter = ("source_kind", "status", "match_status")
    readonly_fields = ("raw_extract", "confidence", "error_message", "created_at", "updated_at")
