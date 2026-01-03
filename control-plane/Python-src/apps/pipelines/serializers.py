"""
Pipeline API serializers
"""
from rest_framework import serializers
from apps.pipelines.models import Pipeline, PipelineConfig
from apps.pipelines.parser import parse_pipeline_yaml


class PipelineConfigSerializer(serializers.ModelSerializer):
    """Serializer for pipeline configuration."""

    class Meta:
        model = PipelineConfig
        fields = [
            'id', 'version', 'config_yaml', 'parsed_config',
            'commit_sha', 'commit_message', 'is_valid',
            'validation_errors', 'created_at'
        ]
        read_only_fields = ['id', 'version', 'parsed_config', 'is_valid', 'validation_errors']


class PipelineSerializer(serializers.ModelSerializer):
    """Serializer for Pipeline model."""
    latest_config = serializers.SerializerMethodField()
    execution_count = serializers.SerializerMethodField()

    class Meta:
        model = Pipeline
        fields = [
            'id', 'name', 'slug', 'description',
            'repository_url', 'default_branch', 'config_path',
            'triggers', 'is_active', 'last_execution_at',
            'latest_config', 'execution_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']

    def get_latest_config(self, obj):
        config = obj.get_latest_config()
        if config:
            return PipelineConfigSerializer(config).data
        return None

    def get_execution_count(self, obj):
        return obj.executions.count()


class PipelineCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating pipelines."""
    config_yaml = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Pipeline
        fields = [
            'name', 'slug', 'description',
            'repository_url', 'default_branch', 'config_path',
            'triggers', 'config_yaml'
        ]

    def create(self, validated_data):
        config_yaml = validated_data.pop('config_yaml', None)
        pipeline = super().create(validated_data)

        # Parse and create initial config if provided
        if config_yaml:
            parsed, errors = parse_pipeline_yaml(config_yaml)
            PipelineConfig.objects.create(
                pipeline=pipeline,
                version=1,
                config_yaml=config_yaml,
                parsed_config=parsed,
                is_valid=len(errors) == 0,
                validation_errors=errors,
            )

        return pipeline


class PipelineTriggerSerializer(serializers.Serializer):
    """Serializer for manual pipeline triggering."""
    inputs = serializers.DictField(required=False, default=dict)
    branch = serializers.CharField(required=False, default='main')
    environment = serializers.DictField(required=False, default=dict)
