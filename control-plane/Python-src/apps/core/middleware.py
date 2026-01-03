"""
Tenant middleware for multi-tenant isolation.
"""
from django.conf import settings
from django.http import HttpRequest
from apps.core.context import set_current_tenant, clear_current_tenant


class TenantMiddleware:
    """
    Middleware that identifies the current tenant and sets it in thread-local storage.

    Tenant identification order:
    1. From authenticated user's tenant
    2. From API key header (X-API-Key)
    3. From subdomain (for SaaS mode)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        # Skip tenant identification in self-hosted mode
        if getattr(settings, 'DEPLOYMENT_MODE', 'saas') == 'self_hosted':
            self._set_default_tenant()
        else:
            self._identify_tenant(request)

        try:
            response = self.get_response(request)
        finally:
            clear_current_tenant()

        return response

    def _identify_tenant(self, request: HttpRequest) -> None:
        """Identify and set the current tenant."""
        tenant = None

        # 1. Try to get tenant from authenticated user
        if hasattr(request, 'user') and request.user.is_authenticated:
            if hasattr(request.user, 'tenant'):
                tenant = request.user.tenant

        # 2. Try to get tenant from API key
        if not tenant:
            api_key = request.headers.get('X-API-Key')
            if api_key:
                tenant = self._get_tenant_from_api_key(api_key)

        # 3. Try to get tenant from subdomain
        if not tenant:
            tenant = self._get_tenant_from_subdomain(request)

        if tenant:
            set_current_tenant(tenant)
            request.tenant = tenant
        else:
            request.tenant = None

    def _get_tenant_from_api_key(self, api_key: str):
        """Get tenant from API key."""
        from apps.auth_service.models import APIKey
        import hashlib

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        try:
            api_key_obj = APIKey.objects.select_related('tenant').get(
                key_hash=key_hash,
                is_active=True,
            )
            return api_key_obj.tenant
        except APIKey.DoesNotExist:
            return None

    def _get_tenant_from_subdomain(self, request: HttpRequest):
        """Get tenant from subdomain (SaaS mode)."""
        from apps.tenants.models import Tenant

        host = request.get_host().split(':')[0]  # Remove port
        parts = host.split('.')

        if len(parts) >= 2:
            subdomain = parts[0]
            # Skip common subdomains
            if subdomain not in ('www', 'api', 'app', 'admin'):
                try:
                    return Tenant.objects.get(slug=subdomain, is_active=True)
                except Tenant.DoesNotExist:
                    pass

        return None

    def _set_default_tenant(self) -> None:
        """Set the default tenant for self-hosted mode."""
        from apps.tenants.models import Tenant

        slug = getattr(settings, 'DEFAULT_TENANT_SLUG', 'default')
        try:
            tenant = Tenant.objects.get(slug=slug)
            set_current_tenant(tenant)
        except Tenant.DoesNotExist:
            pass
