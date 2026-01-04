"""
Webhooks URL configuration for Muelsyse-CI
"""
from django.urls import path

from apps.webhooks.views import GitHubWebhookView

app_name = 'webhooks'

urlpatterns = [
    path('github/', GitHubWebhookView.as_view(), name='github-webhook'),
]
