"""
Artifact API views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import FileResponse

from apps.artifacts.models import Artifact, ArtifactDownload
from apps.artifacts.serializers import ArtifactSerializer


class ArtifactViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for artifact management.

    list: Get all artifacts
    retrieve: Get artifact details
    download: Download an artifact
    """
    serializer_class = ArtifactSerializer
    lookup_field = 'id'

    def get_queryset(self):
        queryset = Artifact.objects.filter(tenant=self.request.tenant)

        # Filter by execution
        execution_id = self.request.query_params.get('execution')
        if execution_id:
            queryset = queryset.filter(execution_id=execution_id)

        # Filter by job
        job_id = self.request.query_params.get('job')
        if job_id:
            queryset = queryset.filter(job_id=job_id)

        # Exclude expired by default
        include_expired = self.request.query_params.get('include_expired', 'false')
        if include_expired.lower() != 'true':
            from django.utils import timezone
            queryset = queryset.filter(expires_at__gt=timezone.now())

        return queryset.select_related('execution', 'job')

    @action(detail=True, methods=['get'])
    def download(self, request, id=None):
        """Download an artifact."""
        artifact = self.get_object()

        if artifact.is_expired:
            return Response(
                {'error': 'Artifact has expired'},
                status=status.HTTP_410_GONE
            )

        # Record download
        ArtifactDownload.objects.create(
            artifact=artifact,
            downloaded_by=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )

        # TODO: Implement actual file serving based on storage backend
        # For now, return the storage path
        return Response({
            'download_url': f'/artifacts/download/{artifact.storage_path}',
            'name': artifact.name,
            'size_bytes': artifact.size_bytes,
            'checksum_sha256': artifact.checksum_sha256,
        })

    def destroy(self, request, *args, **kwargs):
        """Delete an artifact."""
        artifact = self.get_object()

        # TODO: Delete from storage backend

        artifact.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
