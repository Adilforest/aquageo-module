"""Catalog API permissions."""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import Role
from accounts.permissions import ROLE_RANK


class ReadOnlyOrEngineer(BasePermission):
    """Public read (viewer); writes require engineer role or higher."""

    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return True
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser:
            return True
        return ROLE_RANK.get(user.role, -1) >= ROLE_RANK[Role.ENGINEER]
