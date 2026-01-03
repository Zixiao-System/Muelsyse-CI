"""
WebSocket URL routing for Muelsyse-CI
"""
from django.urls import re_path
from apps.logs.consumers import LogConsumer
from apps.runners.consumers import RunnerConsumer

websocket_urlpatterns = [
    # Log streaming
    re_path(
        r'ws/logs/(?P<execution_id>[0-9a-f-]+)/$',
        LogConsumer.as_asgi(),
        name='ws-execution-logs'
    ),
    re_path(
        r'ws/logs/(?P<execution_id>[0-9a-f-]+)/(?P<job_id>[0-9a-f-]+)/$',
        LogConsumer.as_asgi(),
        name='ws-job-logs'
    ),

    # Runner communication
    re_path(
        r'ws/runner/(?P<runner_id>[0-9a-f-]+)/$',
        RunnerConsumer.as_asgi(),
        name='ws-runner'
    ),
]
