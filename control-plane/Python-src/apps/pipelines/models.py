"""
Pipeline models for Muelsyse-CI

This module contains the core models for pipeline definition and configuration.
"""
import uuid
from django.db import models
from apps.core.models import TenantAwareModel


class Pipeline(TenantAwareModel):
    """
    Pipeline definition.

    A pipeline represents a CI/CD workflow that can be triggered by various events.
    """
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, db_index=True)
    description = models.TextField(blank=True)

    # Repository configuration
    repository_url = models.URLField(blank=True)
    default_branch = models.CharField(max_length=100, default='main')
    config_path = models.CharField(
        max_length=200,
        default='.muelsyse/pipeline.yml',
        help_text='Path to the pipeline configuration file in the repository'
    )

    # Trigger configuration
    triggers = models.JSONField(
        default=dict,
        help_text='Trigger configuration: push, pull_request, schedule, workflow_dispatch'
    )

    # Webhook secret for verifying incoming webhooks
    webhook_secret = models.CharField(max_length=100, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    last_execution_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['name']
        unique_together = ['tenant', 'slug']
        indexes = [
            models.Index(fields=['tenant', 'is_active']),
        ]

    def __str__(self):
        return self.name

    def get_latest_config(self):
        """Get the latest valid configuration for this pipeline."""
        return self.configs.filter(is_valid=True).order_by('-version').first()


class PipelineConfig(models.Model):
    """
    Versioned pipeline configuration.

    Each time a pipeline's YAML configuration changes, a new version is created.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.CASCADE,
        related_name='configs'
    )
    version = models.PositiveIntegerField()

    # Raw YAML content
    config_yaml = models.TextField()

    # Parsed and validated configuration
    parsed_config = models.JSONField(default=dict)

    # Source information
    commit_sha = models.CharField(max_length=40, blank=True)
    commit_message = models.TextField(blank=True)

    # Validation status
    is_valid = models.BooleanField(default=True)
    validation_errors = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version']
        unique_together = ['pipeline', 'version']

    def __str__(self):
        return f"{self.pipeline.name} v{self.version}"
