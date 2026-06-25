"""Custom user model.

Defined early (before catalog/workflow models) so ``AUTH_USER_MODEL`` is set
before the first real migrations — many models reference the user via
``created_by`` / ``uploaded_by`` / ``reviewer_id`` etc.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    VIEWER = "viewer", "Гость / просмотр"
    ENGINEER = "engineer", "Инженер / аналитик"
    MANAGER = "manager", "Руководитель"
    ADMIN = "admin", "Администратор"


class User(AbstractUser):
    """Project user with an RBAC role (see CLAUDE.md §7)."""

    role = models.CharField(
        "Роль",
        max_length=16,
        choices=Role.choices,
        default=Role.VIEWER,
    )

    class Meta(AbstractUser.Meta):
        pass

    @property
    def is_engineer(self) -> bool:
        return self.role == Role.ENGINEER

    @property
    def is_manager(self) -> bool:
        return self.role == Role.MANAGER

    @property
    def is_admin_role(self) -> bool:
        # Superusers implicitly have admin-level role access.
        return self.role == Role.ADMIN or self.is_superuser
