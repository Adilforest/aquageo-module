from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"
    verbose_name = "Уведомления"

    def ready(self):
        # Connect the AuditLog -> Notification subscriber (issue #28).
        from . import signals  # noqa: F401
