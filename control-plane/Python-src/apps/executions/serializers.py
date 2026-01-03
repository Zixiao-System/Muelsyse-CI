"""
Execution API serializers
"""
from rest_framework import serializers
from apps.executions.models import Execution, Job, Step


class StepSerializer(serializers.ModelSerializer):
    """Serializer for Step model."""
    duration_seconds = serializers.FloatField(read_only=True)

    class Meta:
        model = Step
        fields = [
            'id', 'name', 'order', 'step_type',
            'run_command', 'shell', 'working_directory',
            'uses_action', 'with_inputs', 'env',
            'condition', 'continue_on_error', 'timeout_minutes',
            'status', 'exit_code',
            'started_at', 'finished_at', 'duration_seconds',
            'outputs'
        ]


class JobSerializer(serializers.ModelSerializer):
    """Serializer for Job model."""
    steps = StepSerializer(many=True, read_only=True)
    duration_seconds = serializers.FloatField(read_only=True)
    runner_name = serializers.CharField(source='runner.name', read_only=True, allow_null=True)

    class Meta:
        model = Job
        fields = [
            'id', 'name', 'job_key', 'needs', 'condition',
            'matrix_values', 'runs_on', 'container', 'services',
            'status', 'runner', 'runner_name',
            'queued_at', 'started_at', 'finished_at', 'duration_seconds',
            'timeout_minutes', 'outputs', 'environment',
            'steps', 'created_at'
        ]


class JobSummarySerializer(serializers.ModelSerializer):
    """Summary serializer for Job (without steps)."""
    duration_seconds = serializers.FloatField(read_only=True)
    step_count = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            'id', 'name', 'job_key', 'status',
            'started_at', 'finished_at', 'duration_seconds',
            'step_count'
        ]

    def get_step_count(self, obj):
        return obj.steps.count()


class ExecutionSerializer(serializers.ModelSerializer):
    """Serializer for Execution model."""
    jobs = JobSummarySerializer(many=True, read_only=True)
    duration_seconds = serializers.FloatField(read_only=True)
    pipeline_name = serializers.CharField(source='pipeline.name', read_only=True)
    triggered_by_username = serializers.CharField(
        source='triggered_by.username', read_only=True, allow_null=True
    )

    class Meta:
        model = Execution
        fields = [
            'id', 'pipeline', 'pipeline_name', 'pipeline_config',
            'number', 'trigger_type', 'trigger_info',
            'status', 'queued_at', 'started_at', 'finished_at', 'duration_seconds',
            'environment', 'inputs',
            'concurrency_group', 'concurrency_cancel_in_progress',
            'triggered_by', 'triggered_by_username',
            'jobs', 'created_at'
        ]


class ExecutionListSerializer(serializers.ModelSerializer):
    """List serializer for Execution (lighter weight)."""
    duration_seconds = serializers.FloatField(read_only=True)
    pipeline_name = serializers.CharField(source='pipeline.name', read_only=True)
    job_count = serializers.SerializerMethodField()

    class Meta:
        model = Execution
        fields = [
            'id', 'pipeline', 'pipeline_name',
            'number', 'trigger_type', 'status',
            'started_at', 'finished_at', 'duration_seconds',
            'job_count', 'created_at'
        ]

    def get_job_count(self, obj):
        return obj.jobs.count()
