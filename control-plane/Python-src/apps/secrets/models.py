"""
Secret models for Muelsyse-CI

This module contains models for securely storing secrets and sensitive data.
"""
import uuid
import base64
from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from apps.core.models import TenantAwareModel


class Secret(TenantAwareModel):
    """
    Encrypted secret storage.

    Secrets are encrypted using AES-256 (via Fernet) with a key derived
    from the master secret and tenant ID for isolation.
    """

    class Scope(models.TextChoices):
        ORGANIZATION = 'organization', 'Organization'
        PIPELINE = 'pipeline', 'Pipeline'

    # Pipeline association (null for organization-level secrets)
    pipeline = models.ForeignKey(
        'pipelines.Pipeline',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='secrets'
    )

    name = models.CharField(
        max_length=100,
        help_text='Secret name (e.g., DEPLOY_TOKEN, AWS_SECRET_KEY)'
    )

    # Encrypted value
    encrypted_value = models.BinaryField()

    scope = models.CharField(
        max_length=20,
        choices=Scope.choices,
        default=Scope.ORGANIZATION
    )

    # Audit
    last_updated_by = models.ForeignKey(
        'auth_service.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['name']
        unique_together = ['tenant', 'pipeline', 'name']
        indexes = [
            models.Index(fields=['tenant', 'scope']),
        ]

    def __str__(self):
        return self.name

    def set_value(self, plaintext: str) -> None:
        """Encrypt and store a secret value."""
        fernet = self._get_fernet()
        self.encrypted_value = fernet.encrypt(plaintext.encode())

    def get_value(self) -> str:
        """Decrypt and return the secret value."""
        fernet = self._get_fernet()
        return fernet.decrypt(self.encrypted_value).decode()

    def _get_fernet(self) -> Fernet:
        """Get Fernet instance with tenant-specific key."""
        master_key = settings.SECRET_ENCRYPTION_KEY.encode()
        tenant_salt = str(self.tenant_id).encode()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=tenant_salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key))
        return Fernet(key)


class SecretVersion(models.Model):
    """
    Secret version for audit trail.

    Stores encrypted previous values of secrets for auditing purposes.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    secret = models.ForeignKey(
        Secret,
        on_delete=models.CASCADE,
        related_name='versions'
    )

    version = models.PositiveIntegerField()
    encrypted_value = models.BinaryField()

    updated_by = models.ForeignKey(
        'auth_service.User',
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version']
        unique_together = ['secret', 'version']

    def __str__(self):
        return f"{self.secret.name} v{self.version}"
