"""
Self-hosted deployment settings.
Disables multi-tenancy and uses a single default tenant.
"""
from .base import *

DEPLOYMENT_MODE = 'self_hosted'

# Remove tenant middleware for self-hosted mode
MIDDLEWARE = [m for m in MIDDLEWARE if 'Tenant' not in m]

# Default tenant ID for self-hosted deployments
DEFAULT_TENANT_SLUG = 'default'

# Simplified permissions - no tenant isolation needed
REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = [
    'rest_framework.permissions.IsAuthenticated',
]
