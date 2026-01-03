"""
Custom authentication backends for Muelsyse-CI
"""
import hashlib
from rest_framework import authentication, exceptions
from django.utils import timezone


class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    Authentication backend for API keys.

    Usage:
        curl -H "X-API-Key: mci_xxxx" https://api.example.com/...
    """

    keyword = 'X-API-Key'

    def authenticate(self, request):
        api_key = request.headers.get(self.keyword)
        if not api_key:
            return None

        # Validate and get API key object
        key_obj = self._validate_api_key(api_key)
        if not key_obj:
            raise exceptions.AuthenticationFailed('Invalid API key.')

        # Record usage
        key_obj.record_usage()

        # Set tenant on request
        request.tenant = key_obj.tenant
        request.api_key = key_obj

        return (key_obj.user, key_obj)

    def _validate_api_key(self, raw_key: str):
        """Validate API key and return APIKey object if valid."""
        from apps.auth_service.models import APIKey

        # Check format
        if not raw_key.startswith('mci_'):
            return None

        # Hash the key
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        try:
            api_key = APIKey.objects.select_related('user', 'tenant').get(
                key_hash=key_hash
            )
        except APIKey.DoesNotExist:
            return None

        # Check validity
        if not api_key.is_valid:
            return None

        return api_key

    def authenticate_header(self, request):
        return self.keyword
