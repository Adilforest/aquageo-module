from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("kind", "recipient", "read", "created_at")
    list_filter = ("kind", "read")
    search_fields = ("recipient__username", "message")
    readonly_fields = ("created_at", "updated_at")
