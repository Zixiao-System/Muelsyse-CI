"""
Custom permissions for Muelsyse-CI
"""
from rest_framework import permissions


class TenantPermission(permissions.BasePermission):
    """
    Permission class that ensures users can only access their own tenant's data.
    """
    message = "You do not have permission to access this resource."

    def has_permission(self, request, view):
        # Allow if tenant is set (authenticated and identified)
        return hasattr(request, 'tenant') and request.tenant is not None

    def has_object_permission(self, request, view, obj):
        # Check if object belongs to user's tenant
        if hasattr(obj, 'tenant'):
            return obj.tenant == request.tenant
        return True


class RolePermission(permissions.BasePermission):
    """
    Permission class based on user roles.

    Roles hierarchy:
    - owner: Full access
    - admin: Manage pipelines, runners, secrets, view users
    - developer: Manage pipelines, trigger executions
    - viewer: Read-only access
    """

    ROLE_PERMISSIONS = {
        'owner': ['*'],
        'admin': [
            'pipeline:read', 'pipeline:write', 'pipeline:delete',
            'runner:read', 'runner:write', 'runner:delete',
            'secret:read', 'secret:write', 'secret:delete',
            'execution:read', 'execution:write',
            'user:read',
        ],
        'developer': [
            'pipeline:read', 'pipeline:write',
            'execution:read', 'execution:write',
            'secret:read',
            'artifact:read', 'artifact:write',
        ],
        'viewer': [
            'pipeline:read',
            'execution:read',
            'artifact:read',
        ],
    }

    def has_permission(self, request, view):
        required_permission = getattr(view, 'required_permission', None)
        if not required_permission:
            return True

        if not request.user.is_authenticated:
            return False

        user_role = getattr(request.user, 'role', 'viewer')
        user_permissions = self.ROLE_PERMISSIONS.get(user_role, [])

        # Check wildcard permission
        if '*' in user_permissions:
            return True

        return required_permission in user_permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """Permission class for owner/admin only actions."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.role in ('owner', 'admin')
