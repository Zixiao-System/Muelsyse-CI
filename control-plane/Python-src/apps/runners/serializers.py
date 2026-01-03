"""
Runner API serializers
"""
from rest_framework import serializers
from apps.runners.models import Runner


class RunnerSerializer(serializers.ModelSerializer):
    """Serializer for Runner model."""
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = Runner
        fields = [
            'id', 'name', 'description', 'runner_type',
            'labels', 'capabilities', 'status',
            'last_heartbeat', 'system_info',
            'max_concurrent_jobs', 'current_jobs', 'is_available',
            'version', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'token_hash', 'status', 'last_heartbeat',
            'system_info', 'current_jobs', 'version',
            'created_at', 'updated_at'
        ]


class RunnerCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating runners."""

    class Meta:
        model = Runner
        fields = ['name', 'description', 'labels', 'max_concurrent_jobs']


class RunnerTokenSerializer(serializers.Serializer):
    """Serializer for runner token generation."""
    name = serializers.CharField(max_length=100)
    labels = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
