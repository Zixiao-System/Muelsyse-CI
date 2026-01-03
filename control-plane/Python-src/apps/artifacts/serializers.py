"""
Artifact API serializers
"""
from rest_framework import serializers
from apps.artifacts.models import Artifact


class ArtifactSerializer(serializers.ModelSerializer):
    """Serializer for Artifact model."""
    size_mb = serializers.FloatField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    execution_number = serializers.IntegerField(source='execution.number', read_only=True)
    job_name = serializers.CharField(source='job.name', read_only=True)

    class Meta:
        model = Artifact
        fields = [
            'id', 'name', 'execution', 'execution_number',
            'job', 'job_name',
            'storage_path', 'size_bytes', 'size_mb',
            'checksum_sha256', 'file_count',
            'is_compressed', 'compression_type',
            'retention_days', 'expires_at', 'is_expired',
            'created_at'
        ]
        read_only_fields = ['id', 'storage_path', 'created_at']
