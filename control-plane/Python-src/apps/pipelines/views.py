"""
Pipeline API views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.utils.text import slugify

from apps.pipelines.models import Pipeline, PipelineConfig
from apps.pipelines.serializers import (
    PipelineSerializer,
    PipelineCreateSerializer,
    PipelineConfigSerializer,
    PipelineTriggerSerializer,
)
from apps.pipelines.parser import parse_pipeline_yaml
from apps.executions.models import Execution
from apps.core.permissions import RolePermission


class PipelineViewSet(viewsets.ModelViewSet):
    """
    API endpoint for pipeline management.

    list: Get all pipelines for the current tenant
    create: Create a new pipeline
    retrieve: Get a specific pipeline
    update: Update a pipeline
    destroy: Delete a pipeline
    trigger: Manually trigger a pipeline execution
    configs: Get configuration versions for a pipeline
    """
    serializer_class = PipelineSerializer
    lookup_field = 'id'

    def get_queryset(self):
        return Pipeline.objects.filter(tenant=self.request.tenant)

    def get_serializer_class(self):
        if self.action == 'create':
            return PipelineCreateSerializer
        return PipelineSerializer

    def perform_create(self, serializer):
        # Auto-generate slug if not provided
        name = serializer.validated_data.get('name', '')
        slug = serializer.validated_data.get('slug') or slugify(name)

        serializer.save(tenant=self.request.tenant, slug=slug)

    @action(detail=True, methods=['post'])
    def trigger(self, request, id=None):
        """
        Manually trigger a pipeline execution.

        Request body:
        {
            "inputs": {"key": "value"},  // workflow_dispatch inputs
            "branch": "main",            // branch to build
            "environment": {}            // additional env vars
        }
        """
        pipeline = self.get_object()

        serializer = PipelineTriggerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get latest config
        config = pipeline.get_latest_config()
        if not config or not config.is_valid:
            return Response(
                {'error': 'No valid pipeline configuration found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create execution
        execution = Execution.objects.create(
            tenant=request.tenant,
            pipeline=pipeline,
            pipeline_config=config,
            number=Execution.objects.filter(pipeline=pipeline).count() + 1,
            trigger_type=Execution.TriggerType.MANUAL,
            trigger_info={
                'user_id': str(request.user.id),
                'username': request.user.username,
                'branch': serializer.validated_data.get('branch', 'main'),
            },
            inputs=serializer.validated_data.get('inputs', {}),
            environment=serializer.validated_data.get('environment', {}),
            triggered_by=request.user,
        )

        # Update pipeline last execution time
        pipeline.last_execution_at = timezone.now()
        pipeline.save(update_fields=['last_execution_at'])

        # TODO: Queue execution for processing

        return Response({
            'execution_id': str(execution.id),
            'number': execution.number,
            'status': execution.status,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def configs(self, request, id=None):
        """Get configuration versions for a pipeline."""
        pipeline = self.get_object()
        configs = pipeline.configs.all()[:20]  # Last 20 versions
        serializer = PipelineConfigSerializer(configs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_config(self, request, id=None):
        """Update pipeline configuration from YAML."""
        pipeline = self.get_object()

        yaml_content = request.data.get('config_yaml')
        if not yaml_content:
            return Response(
                {'error': 'config_yaml is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse YAML
        parsed, errors = parse_pipeline_yaml(yaml_content)

        # Get next version number
        last_version = pipeline.configs.order_by('-version').first()
        next_version = (last_version.version + 1) if last_version else 1

        # Create new config
        config = PipelineConfig.objects.create(
            pipeline=pipeline,
            version=next_version,
            config_yaml=yaml_content,
            parsed_config=parsed,
            is_valid=len(errors) == 0,
            validation_errors=errors,
            commit_sha=request.data.get('commit_sha', ''),
            commit_message=request.data.get('commit_message', ''),
        )

        return Response(
            PipelineConfigSerializer(config).data,
            status=status.HTTP_201_CREATED
        )
