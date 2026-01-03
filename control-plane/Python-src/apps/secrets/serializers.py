"""
Secret API serializers
"""
from rest_framework import serializers
from apps.secrets.models import Secret


class SecretSerializer(serializers.ModelSerializer):
    """
    Serializer for Secret model.

    Note: The actual value is never returned in API responses.
    """

    class Meta:
        model = Secret
        fields = [
            'id', 'name', 'scope', 'pipeline',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SecretCreateSerializer(serializers.Serializer):
    """Serializer for creating/updating secrets."""
    name = serializers.CharField(max_length=100)
    value = serializers.CharField(write_only=True)
    pipeline = serializers.UUIDField(required=False, allow_null=True)


class SecretUpdateSerializer(serializers.Serializer):
    """Serializer for updating secret value."""
    value = serializers.CharField(write_only=True)
