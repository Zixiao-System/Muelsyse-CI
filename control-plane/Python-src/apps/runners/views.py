"""
Runner API views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.runners.models import Runner
from apps.runners.serializers import (
    RunnerSerializer,
    RunnerCreateSerializer,
    RunnerTokenSerializer,
)
from apps.core.permissions import IsOwnerOrAdmin


class RunnerViewSet(viewsets.ModelViewSet):
    """
    API endpoint for runner management.

    list: Get all runners for the current tenant
    create: Register a new runner
    retrieve: Get a specific runner
    update: Update runner settings
    destroy: Delete a runner
    generate_token: Generate a new runner registration token
    """
    serializer_class = RunnerSerializer
    lookup_field = 'id'

    def get_queryset(self):
        queryset = Runner.objects.all()

        # In SaaS mode, filter by tenant (include shared runners)
        if self.request.tenant:
            queryset = queryset.filter(
                tenant=self.request.tenant
            ) | queryset.filter(
                runner_type=Runner.RunnerType.SHARED
            )

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by label
        label = self.request.query_params.get('label')
        if label:
            queryset = queryset.filter(labels__contains=[label])

        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return RunnerCreateSerializer
        return RunnerSerializer

    @action(detail=False, methods=['post'], permission_classes=[IsOwnerOrAdmin])
    def generate_token(self, request):
        """
        Generate a new runner registration token.

        This token should be used to configure a new runner to connect
        to this control plane.
        """
        serializer = RunnerTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.validated_data['name']
        labels = serializer.validated_data.get('labels', [])

        # Generate token
        raw_token, token_hash = Runner.generate_token()

        # Create runner record
        runner = Runner.objects.create(
            tenant=request.tenant,
            name=name,
            token_hash=token_hash,
            runner_type=Runner.RunnerType.SELF_HOSTED,
            labels=labels,
            status=Runner.Status.OFFLINE,
        )

        return Response({
            'runner_id': str(runner.id),
            'name': runner.name,
            'token': raw_token,  # Only returned once!
            'message': 'Save this token securely. It will not be shown again.',
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def enable(self, request, id=None):
        """Enable a runner for job execution."""
        runner = self.get_object()
        if runner.status == Runner.Status.MAINTENANCE:
            runner.status = Runner.Status.OFFLINE
            runner.save(update_fields=['status'])
        return Response({'status': runner.status})

    @action(detail=True, methods=['post'])
    def disable(self, request, id=None):
        """Disable a runner (put in maintenance mode)."""
        runner = self.get_object()
        runner.status = Runner.Status.MAINTENANCE
        runner.save(update_fields=['status'])
        return Response({'status': runner.status})
