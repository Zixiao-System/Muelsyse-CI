"""
Artifact models for Muelsyse-CI

This module contains models for storing build artifacts.
"""
import uuid
from django.db import models
from django.utils import timezone

from apps.core.models import TenantAwareModel


class Artifact(TenantAwareModel):
    """
    Build artifact storage.

    Artifacts are files produced by jobs that can be downloaded
    or used by dependent jobs.
    """
    execution = models.ForeignKey(
        'executions.Execution',
        on_delete=models.CASCADE,
        related_name='artifacts'
    )
    job = models.ForeignKey(
        'executions.Job',
        on_delete=models.CASCADE,
        related_name='artifacts'
    )

    name = models.CharField(
        max_length=200,
        help_text='Artifact name for reference'
    )

    # Storage
    storage_path = models.CharField(
        max_length=500,
        help_text='Path in storage backend'
    )
    size_bytes = models.BigIntegerField()
    checksum_sha256 = models.CharField(max_length=64)

    # Retention
    retention_days = models.PositiveIntegerField(default=30)
    expires_at = models.DateTimeField()

    # Metadata
    file_count = models.PositiveIntegerField(default=1)
    is_compressed = models.BooleanField(default=True)
    compression_type = models.CharField(
        max_length=20,
        default='gzip',
        blank=True
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['execution', 'name']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.execution})"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(
                days=self.retention_days
            )
        super().save(*args, **kwargs)

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)


class ArtifactDownload(models.Model):
    """
    Artifact download tracking for audit and analytics.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    artifact = models.ForeignKey(
        Artifact,
        on_delete=models.CASCADE,
        related_name='downloads'
    )

    downloaded_by = models.ForeignKey(
        'auth_service.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    downloaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-downloaded_at']

    def __str__(self):
        return f"{self.artifact.name} downloaded at {self.downloaded_at}"
