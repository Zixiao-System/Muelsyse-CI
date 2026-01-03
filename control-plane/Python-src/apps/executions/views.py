"""
Execution API views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from apps.executions.models import Execution, Job, Step
from apps.executions.serializers import (
    ExecutionSerializer,
    ExecutionListSerializer,
    JobSerializer,
    StepSerializer,
)
from apps.logs.models import LogChunk


class ExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for execution management.

    list: Get all executions for the current tenant
    retrieve: Get a specific execution with jobs
    cancel: Cancel a running execution
    retry: Retry a failed execution
    """
    serializer_class = ExecutionSerializer
    lookup_field = 'id'

    def get_queryset(self):
        queryset = Execution.objects.filter(tenant=self.request.tenant)

        # Filter by pipeline
        pipeline_id = self.request.query_params.get('pipeline')
        if pipeline_id:
            queryset = queryset.filter(pipeline_id=pipeline_id)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.select_related('pipeline', 'triggered_by')

    def get_serializer_class(self):
        if self.action == 'list':
            return ExecutionListSerializer
        return ExecutionSerializer

    @action(detail=True, methods=['post'])
    def cancel(self, request, id=None):
        """Cancel a running execution."""
        execution = self.get_object()

        if execution.status not in ['pending', 'queued', 'running']:
            return Response(
                {'error': 'Can only cancel pending, queued, or running executions'},
                status=status.HTTP_400_BAD_REQUEST
            )

        execution.status = Execution.Status.CANCELLED
        execution.finished_at = timezone.now()
        execution.save(update_fields=['status', 'finished_at'])

        # Cancel all pending/running jobs
        execution.jobs.filter(
            status__in=['pending', 'queued', 'running']
        ).update(
            status=Job.Status.CANCELLED,
            finished_at=timezone.now()
        )

        return Response({'status': 'cancelled'})

    @action(detail=True, methods=['post'])
    def retry(self, request, id=None):
        """Retry a failed execution."""
        execution = self.get_object()

        if execution.status not in ['failed', 'cancelled', 'timeout']:
            return Response(
                {'error': 'Can only retry failed, cancelled, or timed out executions'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create a new execution
        new_execution = Execution.objects.create(
            tenant=execution.tenant,
            pipeline=execution.pipeline,
            pipeline_config=execution.pipeline_config,
            number=Execution.objects.filter(pipeline=execution.pipeline).count() + 1,
            trigger_type=Execution.TriggerType.MANUAL,
            trigger_info={
                'retry_of': str(execution.id),
                'user_id': str(request.user.id),
                'username': request.user.username,
            },
            inputs=execution.inputs,
            environment=execution.environment,
            triggered_by=request.user,
        )

        # TODO: Queue new execution for processing

        return Response({
            'execution_id': str(new_execution.id),
            'number': new_execution.number,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def jobs(self, request, id=None):
        """Get all jobs for an execution."""
        execution = self.get_object()
        jobs = execution.jobs.all()
        serializer = JobSerializer(jobs, many=True)
        return Response(serializer.data)


class JobViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for job details."""
    serializer_class = JobSerializer
    lookup_field = 'id'

    def get_queryset(self):
        return Job.objects.filter(
            execution__tenant=self.request.tenant
        ).select_related('execution', 'runner')

    @action(detail=True, methods=['get'])
    def steps(self, request, id=None):
        """Get all steps for a job."""
        job = self.get_object()
        steps = job.steps.all()
        serializer = StepSerializer(steps, many=True)
        return Response(serializer.data)


class StepViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for step details and logs."""
    serializer_class = StepSerializer
    lookup_field = 'id'

    def get_queryset(self):
        return Step.objects.filter(
            job__execution__tenant=self.request.tenant
        ).select_related('job')

    @action(detail=True, methods=['get'])
    def logs(self, request, id=None):
        """Get logs for a step."""
        step = self.get_object()

        # Pagination
        offset = int(request.query_params.get('offset', 0))
        limit = int(request.query_params.get('limit', 1000))

        logs = LogChunk.objects.filter(step=step).order_by('chunk_number')[offset:offset+limit]

        return Response({
            'step_id': str(step.id),
            'total_chunks': step.log_chunks.count(),
            'logs': [
                {
                    'chunk_number': log.chunk_number,
                    'content': log.content,
                    'level': log.level,
                    'timestamp': log.timestamp.isoformat(),
                }
                for log in logs
            ]
        })
