"""DRF permissions. Role checks only — business rules stay in the domain."""

from rest_framework.permissions import BasePermission

from domain.entities.user import Role


class IsAdmin(BasePermission):
    message = "Admin role required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user is not None
            and getattr(user, "is_authenticated", False)
            and getattr(user, "role", None) == Role.ADMIN
        )