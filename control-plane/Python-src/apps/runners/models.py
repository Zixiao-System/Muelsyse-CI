"""
Runner models for Muelsyse-CI

This module contains models for runner registration and management.
"""
import uuid
import secrets
import hashlib
from django.db import models
from django.utils import timezone


class Runner(models.Model):
    """
    Runner instance that executes jobs.

    Runners can be:
    - Shared: Available to all tenants (SaaS mode)
    - Dedicated: Assigned to a specific tenant
    - Self-hosted: Managed by the tenant themselves
    """

    class RunnerType(models.TextChoices):
        SHARED = 'shared', 'Shared'
        DEDICATED = 'dedicated', 'Dedicated'
        SELF_HOSTED = 'self_hosted', 'Self-Hosted'

    class Status(models.TextChoices):
        ONLINE = 'online', 'Online'
        OFFLINE = 'offline', 'Offline'
        BUSY = 'busy', 'Busy'
        MAINTENANCE = 'maintenance', 'Maintenance'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Tenant association (null for shared runners)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='runners'
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Authentication
    token_hash = models.CharField(max_length=128, unique=True)

    # Runner type
    runner_type = models.CharField(
        max_length=20,
        choices=RunnerType.choices,
        default=RunnerType.SELF_HOSTED
    )

    # Labels for job matching (e.g., ['linux', 'docker', 'gpu'])
    labels = models.JSONField(default=list)

    # Capabilities (what executors are available)
    capabilities = models.JSONField(
        default=dict,
        help_text='Available executors: docker, shell, etc.'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OFFLINE
    )

    # Heartbeat tracking
    last_heartbeat = models.DateTimeField(null=True, blank=True)

    # System information (reported by runner)
    system_info = models.JSONField(
        default=dict,
        help_text='OS, CPU, memory, etc.'
    )

    # Capacity
    max_concurrent_jobs = models.PositiveIntegerField(default=2)
    current_jobs = models.PositiveIntegerField(default=0)

    # Version
    version = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['status', 'runner_type']),
            models.Index(fields=['tenant', 'status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.status})"

    @classmethod
    def generate_token(cls) -> tuple[str, str]:
        """Generate a new runner token and return (raw_token, hash)."""
        raw_token = f"mci_runner_{secrets.token_urlsafe(32)}"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        return raw_token, token_hash

    @property
    def is_available(self) -> bool:
        """Check if runner is available for new jobs."""
        return (
            self.status == self.Status.ONLINE and
            self.current_jobs < self.max_concurrent_jobs
        )

    def update_heartbeat(self, system_info: dict = None) -> None:
        """Update runner heartbeat."""
        self.last_heartbeat = timezone.now()
        if self.status == self.Status.OFFLINE:
            self.status = self.Status.ONLINE
        if system_info:
            self.system_info = system_info
        self.save(update_fields=['last_heartbeat', 'status', 'system_info', 'updated_at'])

    def check_offline(self, threshold_seconds: int = 90) -> bool:
        """Check if runner should be marked as offline."""
        if self.last_heartbeat is None:
            return True
        elapsed = (timezone.now() - self.last_heartbeat).total_seconds()
        return elapsed > threshold_seconds

    def matches_labels(self, required_labels: list) -> bool:
        """Check if runner has all required labels."""
        return set(required_labels).issubset(set(self.labels))
