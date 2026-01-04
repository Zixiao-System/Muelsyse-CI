"""
Muelsyse-CI API v1 URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.pipelines.views import PipelineViewSet
from apps.executions.views import ExecutionViewSet, JobViewSet, StepViewSet
from apps.runners.views import RunnerViewSet
from apps.secrets.views import SecretViewSet
from apps.artifacts.views import ArtifactViewSet
from apps.auth_service.views import AuthViewSet, APIKeyViewSet

router = DefaultRouter()
router.register(r'pipelines', PipelineViewSet, basename='pipeline')
router.register(r'executions', ExecutionViewSet, basename='execution')
router.register(r'jobs', JobViewSet, basename='job')
router.register(r'steps', StepViewSet, basename='step')
router.register(r'runners', RunnerViewSet, basename='runner')
router.register(r'secrets', SecretViewSet, basename='secret')
router.register(r'artifacts', ArtifactViewSet, basename='artifact')
router.register(r'api-keys', APIKeyViewSet, basename='api-key')

urlpatterns = [
    path('', include(router.urls)),

    # Authentication endpoints
    path('auth/', include([
        path('login/', AuthViewSet.as_view({'post': 'login'}), name='auth-login'),
        path('logout/', AuthViewSet.as_view({'post': 'logout'}), name='auth-logout'),
        path('refresh/', AuthViewSet.as_view({'post': 'refresh'}), name='auth-refresh'),
        path('me/', AuthViewSet.as_view({'get': 'me'}), name='auth-me'),
    ])),

    # Webhooks endpoints
    path('webhooks/', include('apps.webhooks.urls', namespace='webhooks')),
]
