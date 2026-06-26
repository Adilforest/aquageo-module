from django.contrib import admin

from .models import Application, ApprovalOrder, Signature


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("kind", "structure", "status", "submitted_by", "reviewer", "decided_at")
    list_filter = ("status", "kind")
    search_fields = ("structure__name_ru",)
    readonly_fields = ("submitted_at", "decided_at", "created_at", "updated_at")


@admin.register(Signature)
class SignatureAdmin(admin.ModelAdmin):
    list_display = ("application", "signer", "valid", "signed_at")
    list_filter = ("valid",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ApprovalOrder)
class ApprovalOrderAdmin(admin.ModelAdmin):
    list_display = ("number", "application", "issued_at")
    search_fields = ("number",)
    readonly_fields = ("created_at", "updated_at")
