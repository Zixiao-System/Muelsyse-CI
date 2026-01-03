"""
Execution models for Muelsyse-CI

This module contains models for tracking pipeline executions, jobs, and steps.
"""
import uuid
from django.db import models
from apps.core.models import TenantAwareModel


class Execution(TenantAwareModel):
    """
    Pipeline execution record.

    An execution represents a single run of a pipeline, triggered by push, PR, schedule, etc.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        QUEUED = 'queued', 'Queued'
        RUNNING = 'running', 'Running'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'
        TIMEOUT = 'timeout', 'Timeout'
        SKIPPED = 'skipped', 'Skipped'

    class TriggerType(models.TextChoices):
        PUSH = 'push', 'Push'
        PULL_REQUEST = 'pull_request', 'Pull Request'
        SCHEDULE = 'schedule', 'Schedule'
        MANUAL = 'manual', 'Manual'
        WEBHOOK = 'webhook', 'Webhook'
        API = 'api', 'API'

    # Pipeline reference
    pipeline = models.ForeignKey(
        'pipelines.Pipeline',
        on_delete=models.CASCADE,
        related_name='executions'
    )
    pipeline_config = models.ForeignKey(
        'pipelines.PipelineConfig',
        on_delete=models.SET_NULL,
        null=True,
        related_name='executions'
    )

    # Execution number (auto-incrementing per pipeline)
    number = models.PositiveIntegerField()

    # Trigger information
    trigger_type = models.CharField(
        max_length=20,
        choices=TriggerType.choices
    )
    trigger_info = models.JSONField(
        default=dict,
        help_text='Details about the trigger: commit SHA, branch, user, etc.'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Timing
    queued_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    # Environment and inputs
    environment = models.JSONField(
        default=dict,
        help_text='Environment variables for this execution'
    )
    inputs = models.JSONField(
        default=dict,
        help_text='Inputs for workflow_dispatch trigger'
    )

    # Concurrency control
    concurrency_group = models.CharField(max_length=200, blank=True)
    concurrency_cancel_in_progress = models.BooleanField(default=False)

    # User who triggered (if manual/API)
    triggered_by = models.ForeignKey(
        'auth_service.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triggered_executions'
    )

    class Meta:
        ordering = ['-created_at']
        unique_together = ['pipeline', 'number']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['pipeline', '-number']),
            models.Index(fields=['status', 'queued_at']),
        ]

    def __str__(self):
        return f"{self.pipeline.name} #{self.number}"

    @property
    def duration_seconds(self) -> float | None:
        """Calculate execution duration in seconds."""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    def get_next_number(self) -> int:
        """Get the next execution number for this pipeline."""
        last = Execution.objects.filter(
            pipeline=self.pipeline
        ).order_by('-number').values_list('number', flat=True).first()
        return (last or 0) + 1


class Job(models.Model):
    """
    Job execution record.

    A job is a collection of steps that run on a single runner.
    Jobs within an execution can run in parallel or have dependencies.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        QUEUED = 'queued', 'Queued'
        RUNNING = 'running', 'Running'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'
        TIMEOUT = 'timeout', 'Timeout'
        SKIPPED = 'skipped', 'Skipped'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    execution = models.ForeignKey(
        Execution,
        on_delete=models.CASCADE,
        related_name='jobs'
    )

    # Job identification
    name = models.CharField(max_length=200)
    job_key = models.CharField(
        max_length=100,
        help_text='Key used in YAML (e.g., "build", "test")'
    )

    # Dependencies
    needs = models.JSONField(
        default=list,
        help_text='List of job keys this job depends on'
    )

    # Condition
    condition = models.TextField(
        blank=True,
        help_text='if: condition expression'
    )

    # Matrix instance values
    matrix_values = models.JSONField(
        default=dict,
        help_text='Matrix variable values for this job instance'
    )

    # Runner assignment
    runner = models.ForeignKey(
        'runners.Runner',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='jobs'
    )
    runs_on = models.JSONField(
        default=list,
        help_text='Required runner labels'
    )

    # Container configuration
    container = models.JSONField(
        default=dict,
        help_text='Container configuration: image, options, env, volumes'
    )

    # Services
    services = models.JSONField(
        default=dict,
        help_text='Service containers for this job'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Timing
    queued_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    # Timeout
    timeout_minutes = models.PositiveIntegerField(default=60)

    # Outputs
    outputs = models.JSONField(
        default=dict,
        help_text='Job outputs that can be referenced by dependent jobs'
    )

    # Environment
    environment = models.JSONField(
        default=dict,
        help_text='Environment variables for this job'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['execution', 'status']),
            models.Index(fields=['runner', 'status']),
        ]

    def __str__(self):
        return f"{self.execution} / {self.name}"

    @property
    def duration_seconds(self) -> float | None:
        """Calculate job duration in seconds."""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    def check_dependencies_satisfied(self) -> bool:
        """Check if all dependencies have completed successfully."""
        if not self.needs:
            return True

        dependent_jobs = Job.objects.filter(
            execution=self.execution,
            job_key__in=self.needs
        )

        for job in dependent_jobs:
            if job.status != self.Status.SUCCESS:
                return False

        return True


class Step(models.Model):
    """
    Step execution record.

    A step is a single task within a job: running a command or using an action.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'
        TIMEOUT = 'timeout', 'Timeout'
        SKIPPED = 'skipped', 'Skipped'

    class StepType(models.TextChoices):
        RUN = 'run', 'Run Command'
        USES = 'uses', 'Use Action'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='steps'
    )

    # Step identification
    name = models.CharField(max_length=200)
    order = models.PositiveIntegerField()

    # Step type
    step_type = models.CharField(
        max_length=20,
        choices=StepType.choices
    )

    # Run configuration
    run_command = models.TextField(
        blank=True,
        help_text='Shell command to run'
    )
    shell = models.CharField(max_length=20, default='bash')
    working_directory = models.CharField(max_length=500, blank=True)

    # Uses configuration (for actions)
    uses_action = models.CharField(
        max_length=200,
        blank=True,
        help_text='Action reference: owner/repo@version'
    )
    with_inputs = models.JSONField(
        default=dict,
        help_text='Inputs for the action'
    )

    # Environment
    env = models.JSONField(
        default=dict,
        help_text='Environment variables for this step'
    )

    # Condition and error handling
    condition = models.TextField(
        blank=True,
        help_text='if: condition expression'
    )
    continue_on_error = models.BooleanField(default=False)
    timeout_minutes = models.PositiveIntegerField(default=60)

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    exit_code = models.IntegerField(null=True, blank=True)

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    # Outputs
    outputs = models.JSONField(
        default=dict,
        help_text='Step outputs set via ::set-output'
    )

    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['job', 'order']),
        ]

    def __str__(self):
        return f"{self.job} / Step {self.order}: {self.name}"

    @property
    def duration_seconds(self) -> float | None:
        """Calculate step duration in seconds."""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None
