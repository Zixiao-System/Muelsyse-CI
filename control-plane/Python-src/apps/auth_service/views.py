"""
Authentication API views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

from apps.auth_service.models import User, APIKey


class AuthViewSet(viewsets.ViewSet):
    """Authentication endpoints."""

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        """Login with username/password and get JWT tokens."""
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if not user:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {'error': 'Account is disabled'},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'tenant_id': str(user.tenant_id) if user.tenant else None,
            }
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """Logout and invalidate refresh token."""
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass

        return Response({'message': 'Logged out successfully'})

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def refresh(self, request):
        """Refresh access token."""
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            refresh = RefreshToken(refresh_token)
            return Response({
                'access': str(refresh.access_token),
            })
        except Exception as e:
            return Response(
                {'error': 'Invalid refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Get current user info."""
        user = request.user
        return Response({
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'tenant_id': str(user.tenant_id) if user.tenant else None,
            'tenant_name': user.tenant.name if user.tenant else None,
        })


class APIKeyViewSet(viewsets.ModelViewSet):
    """API Key management."""

    def get_queryset(self):
        return APIKey.objects.filter(
            tenant=self.request.tenant,
            user=self.request.user
        )

    def list(self, request):
        """List user's API keys."""
        api_keys = self.get_queryset()
        return Response([
            {
                'id': str(key.id),
                'name': key.name,
                'key_prefix': key.key_prefix,
                'scopes': key.scopes,
                'is_active': key.is_active,
                'expires_at': key.expires_at,
                'last_used_at': key.last_used_at,
                'created_at': key.created_at,
            }
            for key in api_keys
        ])

    def create(self, request):
        """Create a new API key."""
        name = request.data.get('name')
        scopes = request.data.get('scopes', ['*'])
        expires_at = request.data.get('expires_at')

        if not name:
            return Response(
                {'error': 'Name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate key
        raw_key, key_hash = APIKey.generate_key()

        api_key = APIKey.objects.create(
            tenant=request.tenant,
            user=request.user,
            name=name,
            key_hash=key_hash,
            key_prefix=raw_key[:8],
            scopes=scopes,
            expires_at=expires_at,
        )

        return Response({
            'id': str(api_key.id),
            'name': api_key.name,
            'key': raw_key,  # Only returned once!
            'message': 'Save this key securely. It will not be shown again.',
        }, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        """Delete an API key."""
        try:
            api_key = self.get_queryset().get(pk=pk)
            api_key.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except APIKey.DoesNotExist:
            return Response(
                {'error': 'API key not found'},
                status=status.HTTP_404_NOT_FOUND
            )
