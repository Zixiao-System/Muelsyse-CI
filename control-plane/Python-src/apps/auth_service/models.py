"""
Authentication models for Muelsyse-CI
"""
import uuid
import hashlib
import secrets
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    """
    Custom user model with tenant association and role-based access.
    """

    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        ADMIN = 'admin', 'Admin'
        DEVELOPER = 'developer', 'Developer'
        VIEWER = 'viewer', 'Viewer'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users'
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.DEVELOPER
    )

    # Profile
    avatar_url = models.URLField(blank=True)

    # OAuth info
    oauth_provider = models.CharField(max_length=50, blank=True)
    oauth_id = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['username']

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def is_tenant_admin(self) -> bool:
        return self.role in (self.Role.OWNER, self.Role.ADMIN)


class APIKey(models.Model):
    """
    API Key for programmatic access.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='api_keys'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='api_keys'
    )

    name = models.CharField(max_length=100)
    key_hash = models.CharField(max_length=128, unique=True)  # SHA-256 hash
    key_prefix = models.CharField(max_length=8)  # First 8 chars for identification

    # Permissions
    scopes = models.JSONField(default=list)  # e.g., ['pipeline:read', 'execution:write']

    # Lifecycle
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'

    def __str__(self):
        return f"{self.name} ({self.key_prefix}...)"

    @classmethod
    def generate_key(cls) -> tuple[str, str]:
        """Generate a new API key and return (raw_key, hash)."""
        raw_key = f"mci_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        return raw_key, key_hash

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return timezone.now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return self.is_active and not self.is_expired

    def record_usage(self) -> None:
        """Record API key usage."""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])

    def has_scope(self, scope: str) -> bool:
        """Check if API key has a specific scope."""
        if '*' in self.scopes:
            return True
        if scope in self.scopes:
            return True
        # Check wildcard patterns (e.g., 'pipeline:*')
        resource = scope.split(':')[0]
        return f"{resource}:*" in self.scopes
