"""
Secret API views
"""
from rest_framework import viewsets, status
from rest_framework.response import Response

from apps.secrets.models import Secret, SecretVersion
from apps.secrets.serializers import (
    SecretSerializer,
    SecretCreateSerializer,
    SecretUpdateSerializer,
)
from apps.core.permissions import IsOwnerOrAdmin


class SecretViewSet(viewsets.ModelViewSet):
    """
    API endpoint for secret management.

    Secrets are encrypted at rest and the actual values are never
    returned in API responses.

    list: Get all secrets (without values)
    create: Create a new secret
    update: Update secret value
    destroy: Delete a secret
    """
    serializer_class = SecretSerializer
    lookup_field = 'id'
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        queryset = Secret.objects.filter(tenant=self.request.tenant)

        # Filter by scope
        scope = self.request.query_params.get('scope')
        if scope:
            queryset = queryset.filter(scope=scope)

        # Filter by pipeline
        pipeline_id = self.request.query_params.get('pipeline')
        if pipeline_id:
            queryset = queryset.filter(pipeline_id=pipeline_id)

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = SecretCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.validated_data['name']
        value = serializer.validated_data['value']
        pipeline_id = serializer.validated_data.get('pipeline')

        # Check if secret already exists
        existing = Secret.objects.filter(
            tenant=request.tenant,
            name=name,
            pipeline_id=pipeline_id,
        ).first()

        if existing:
            return Response(
                {'error': f'Secret "{name}" already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create secret
        secret = Secret(
            tenant=request.tenant,
            name=name,
            pipeline_id=pipeline_id,
            scope=Secret.Scope.PIPELINE if pipeline_id else Secret.Scope.ORGANIZATION,
            last_updated_by=request.user,
        )
        secret.set_value(value)
        secret.save()

        return Response(
            SecretSerializer(secret).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        secret = self.get_object()

        serializer = SecretUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Store old version for audit
        last_version = secret.versions.order_by('-version').first()
        next_version = (last_version.version + 1) if last_version else 1

        SecretVersion.objects.create(
            secret=secret,
            version=next_version,
            encrypted_value=secret.encrypted_value,
            updated_by=request.user,
        )

        # Update secret
        secret.set_value(serializer.validated_data['value'])
        secret.last_updated_by = request.user
        secret.save()

        return Response(SecretSerializer(secret).data)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
