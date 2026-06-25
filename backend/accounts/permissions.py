"""Role-based DRF permissions (CLAUDE.md §7).

Roles are hierarchical: admin > manager > engineer > viewer. Each permission
class requires *at least* its role; superusers always pass.
"""
from rest_framework.permissions import BasePermission

from .models import Role

ROLE_RANK = {
    Role.VIEWER: 0,
    Role.ENGINEER: 1,
    Role.MANAGER: 2,
    Role.ADMIN: 3,
}


class HasMinimumRole(BasePermission):
    """Base class: grant access when the user's role rank >= ``required_role``."""

    required_role = Role.VIEWER

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser:
            return True
        return ROLE_RANK.get(user.role, -1) >= ROLE_RANK[self.required_role]


class IsEngineer(HasMinimumRole):
    required_role = Role.ENGINEER


class IsManager(HasMinimumRole):
    required_role = Role.MANAGER


class IsAdmin(HasMinimumRole):
    required_role = Role.ADMIN
