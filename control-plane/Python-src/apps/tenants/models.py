"""
Tenant models for multi-tenancy support.
"""
import uuid
from django.db import models


class Tenant(models.Model):
    """
    Tenant model for multi-tenant isolation.

    In SaaS mode, each organization is a tenant.
    In self-hosted mode, there's a single default tenant.
    """

    class Plan(models.TextChoices):
        FREE = 'free', 'Free'
        PRO = 'pro', 'Professional'
        ENTERPRISE = 'enterprise', 'Enterprise'
        SELF_HOSTED = 'self_hosted', 'Self-Hosted'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    plan = models.CharField(
        max_length=20,
        choices=Plan.choices,
        default=Plan.FREE
    )
    is_active = models.BooleanField(default=True)

    # Tenant-level settings
    settings = models.JSONField(default=dict, blank=True)

    # Resource quotas
    max_runners = models.PositiveIntegerField(default=3)
    max_concurrent_jobs = models.PositiveIntegerField(default=5)
    max_retention_days = models.PositiveIntegerField(default=30)
    storage_quota_mb = models.PositiveIntegerField(default=1024)

    # Usage tracking
    current_storage_mb = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def is_self_hosted(self) -> bool:
        return self.plan == self.Plan.SELF_HOSTED

    def check_quota(self, resource: str) -> bool:
        """Check if tenant is within quota for a resource."""
        quotas = {
            'runners': (self.runner_set.count(), self.max_runners),
            'storage': (self.current_storage_mb, self.storage_quota_mb),
        }
        if resource in quotas:
            current, limit = quotas[resource]
            return current < limit
        return True
