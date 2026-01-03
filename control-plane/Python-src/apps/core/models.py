"""
Tenant-aware base models for Muelsyse-CI
"""
import uuid
from django.db import models
from django.conf import settings


class TimeStampedModel(models.Model):
    """Abstract base model with created/updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """Abstract base model with UUID primary key."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TenantAwareModel(UUIDModel, TimeStampedModel):
    """
    Abstract base model for tenant-aware models.
    All models that need tenant isolation should inherit from this.
    """
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='%(class)s_set',
        db_index=True,
    )

    class Meta:
        abstract = True


class TenantAwareManager(models.Manager):
    """
    Custom manager that automatically filters by current tenant.
    """

    def get_queryset(self):
        from apps.core.context import get_current_tenant
        queryset = super().get_queryset()
        tenant = get_current_tenant()
        if tenant and hasattr(self.model, 'tenant'):
            queryset = queryset.filter(tenant=tenant)
        return queryset
