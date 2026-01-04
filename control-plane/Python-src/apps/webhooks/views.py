"""
GitHub Webhook views for Muelsyse-CI

This module provides API views for receiving and processing GitHub webhooks.
"""
import json
import logging
from typing import Optional

from django.http import HttpRequest
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.webhooks.utils import (
    verify_github_signature,
    get_github_event_type,
    get_github_delivery_id,
)
from apps.webhooks.parsers import (
    parse_github_event,
    PushEvent,
    PullRequestEvent,
)
from apps.pipelines.models import Pipeline
from apps.pipelines.matcher import PipelineMatcher
from apps.executions.models import Execution

logger = logging.getLogger(__name__)


class GitHubWebhookView(APIView):
    """
    API endpoint for receiving GitHub webhooks.

    POST /api/v1/webhooks/github/

    This endpoint receives webhook payloads from GitHub, verifies their
    signatures, parses the events, and triggers matching pipelines.
    """

    # Allow unauthenticated access since webhooks use signature verification
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: HttpRequest) -> Response:
        """
        Handle incoming GitHub webhook.

        The webhook signature is verified using the X-Hub-Signature-256 header.
        Supported events: push, pull_request, ping
        """
        # Get event metadata from headers
        event_type = self._get_event_type(request)
        delivery_id = self._get_delivery_id(request)

        logger.info(
            f"Received GitHub webhook: event={event_type}, delivery={delivery_id}"
        )

        # Handle ping event (used by GitHub to test webhook configuration)
        if event_type == 'ping':
            return self._handle_ping(request)

        # Get raw body for signature verification
        raw_body = request.body

        # Parse payload
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse webhook payload: {e}")
            return Response(
                {'error': 'Invalid JSON payload'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get repository information to find matching pipelines
        repository = payload.get('repository', {})
        repo_url = repository.get('clone_url', '') or repository.get('html_url', '')

        # Find pipelines that match this repository
        pipelines = self._find_pipelines_by_repository(repo_url)

        if not pipelines:
            logger.info(f"No pipelines found for repository: {repo_url}")
            return Response(
                {'message': 'No matching pipelines found'},
                status=status.HTTP_200_OK
            )

        # Verify signature against pipeline webhook secrets
        signature = request.headers.get('X-Hub-Signature-256', '')
        verified_pipeline = self._verify_signature_for_pipelines(
            raw_body, signature, pipelines
        )

        if verified_pipeline is None:
            logger.warning(f"Signature verification failed for delivery: {delivery_id}")
            return Response(
                {'error': 'Invalid signature'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Parse the event
        parsed_event = parse_github_event(event_type, payload)
        if parsed_event is None:
            logger.info(f"Unsupported event type: {event_type}")
            return Response(
                {'message': f'Event type {event_type} is not supported'},
                status=status.HTTP_200_OK
            )

        # Match and trigger pipelines
        triggered_executions = self._process_event(
            event_type, parsed_event, pipelines, delivery_id
        )

        return Response({
            'message': 'Webhook processed successfully',
            'delivery_id': delivery_id,
            'event_type': event_type,
            'executions_triggered': len(triggered_executions),
            'execution_ids': [str(e.id) for e in triggered_executions],
        }, status=status.HTTP_200_OK)

    def _get_event_type(self, request: HttpRequest) -> Optional[str]:
        """Extract GitHub event type from request headers."""
        return (
            request.headers.get('X-GitHub-Event') or
            request.META.get('HTTP_X_GITHUB_EVENT')
        )

    def _get_delivery_id(self, request: HttpRequest) -> Optional[str]:
        """Extract GitHub delivery ID from request headers."""
        return (
            request.headers.get('X-GitHub-Delivery') or
            request.META.get('HTTP_X_GITHUB_DELIVERY')
        )

    def _handle_ping(self, request: HttpRequest) -> Response:
        """Handle GitHub ping event."""
        try:
            payload = json.loads(request.body)
            zen = payload.get('zen', '')
            hook_id = payload.get('hook_id')
            logger.info(f"GitHub ping received: {zen} (hook_id: {hook_id})")
        except json.JSONDecodeError:
            pass

        return Response(
            {'message': 'pong'},
            status=status.HTTP_200_OK
        )

    def _find_pipelines_by_repository(self, repo_url: str) -> list:
        """Find all active pipelines matching the repository URL."""
        if not repo_url:
            return []

        # Normalize URL for matching (handle both HTTPS and SSH URLs)
        normalized_urls = self._normalize_repo_url(repo_url)

        pipelines = []
        for url in normalized_urls:
            matching = Pipeline.objects.filter(
                repository_url__icontains=url,
                is_active=True
            )
            pipelines.extend(list(matching))

        # Remove duplicates
        seen_ids = set()
        unique_pipelines = []
        for p in pipelines:
            if p.id not in seen_ids:
                seen_ids.add(p.id)
                unique_pipelines.append(p)

        return unique_pipelines

    def _normalize_repo_url(self, url: str) -> list:
        """
        Normalize repository URL for matching.

        Returns a list of URL variations to match against.
        """
        urls = [url]

        # Extract owner/repo from various URL formats
        # https://github.com/owner/repo.git
        # git@github.com:owner/repo.git
        # https://github.com/owner/repo

        if 'github.com' in url:
            # Extract owner/repo
            if url.startswith('git@'):
                # SSH format: git@github.com:owner/repo.git
                parts = url.split(':')
                if len(parts) == 2:
                    repo_path = parts[1].replace('.git', '')
                    urls.append(repo_path)
            else:
                # HTTPS format
                repo_path = url.replace('https://github.com/', '')
                repo_path = repo_path.replace('http://github.com/', '')
                repo_path = repo_path.replace('.git', '')
                urls.append(repo_path)

        return urls

    def _verify_signature_for_pipelines(
        self,
        raw_body: bytes,
        signature: str,
        pipelines: list
    ) -> Optional[Pipeline]:
        """
        Verify webhook signature against pipeline webhook secrets.

        Returns the first pipeline whose secret validates the signature,
        or None if no valid signature found.
        """
        for pipeline in pipelines:
            secret = pipeline.webhook_secret
            if secret and verify_github_signature(raw_body, signature, secret):
                return pipeline

        # If no pipeline has a secret configured, allow the webhook
        # (for development/testing purposes)
        has_secrets = any(p.webhook_secret for p in pipelines)
        if not has_secrets:
            logger.warning("No webhook secrets configured, skipping verification")
            return pipelines[0] if pipelines else None

        return None

    def _process_event(
        self,
        event_type: str,
        parsed_event,
        pipelines: list,
        delivery_id: str
    ) -> list:
        """
        Process a parsed event and trigger matching pipelines.

        Returns a list of created Execution objects.
        """
        triggered_executions = []

        for pipeline in pipelines:
            # Get latest valid config
            config = pipeline.get_latest_config()
            if not config or not config.is_valid:
                logger.warning(
                    f"Pipeline {pipeline.name} has no valid configuration, skipping"
                )
                continue

            # Check if event matches pipeline triggers
            matcher = PipelineMatcher(config.parsed_config)

            if event_type == 'push' and isinstance(parsed_event, PushEvent):
                if not matcher.matches_push(parsed_event):
                    logger.debug(
                        f"Push event does not match triggers for pipeline: {pipeline.name}"
                    )
                    continue

                execution = self._create_execution_for_push(
                    pipeline, config, parsed_event, delivery_id
                )

            elif event_type == 'pull_request' and isinstance(parsed_event, PullRequestEvent):
                if not matcher.matches_pull_request(parsed_event):
                    logger.debug(
                        f"PR event does not match triggers for pipeline: {pipeline.name}"
                    )
                    continue

                execution = self._create_execution_for_pr(
                    pipeline, config, parsed_event, delivery_id
                )
            else:
                continue

            if execution:
                triggered_executions.append(execution)
                logger.info(
                    f"Created execution {execution.number} for pipeline: {pipeline.name}"
                )

        return triggered_executions

    def _create_execution_for_push(
        self,
        pipeline: Pipeline,
        config,
        event: PushEvent,
        delivery_id: str
    ) -> Optional[Execution]:
        """Create an execution for a push event."""
        # Skip deleted branches
        if event.deleted:
            logger.info(f"Skipping execution for deleted branch: {event.branch}")
            return None

        # Get next execution number
        last_number = Execution.objects.filter(
            pipeline=pipeline
        ).order_by('-number').values_list('number', flat=True).first() or 0

        trigger_info = {
            'event_type': 'push',
            'delivery_id': delivery_id,
            'ref': event.ref,
            'branch': event.branch,
            'tag': event.tag,
            'commit_sha': event.commit_sha,
            'commit_message': event.head_commit.message if event.head_commit else '',
            'author': event.head_commit.author_name if event.head_commit else '',
            'compare_url': event.compare_url,
            'repository': event.repository.full_name if event.repository else '',
            'sender': event.sender.login if event.sender else '',
        }

        execution = Execution.objects.create(
            tenant=pipeline.tenant,
            pipeline=pipeline,
            pipeline_config=config,
            number=last_number + 1,
            trigger_type=Execution.TriggerType.PUSH,
            trigger_info=trigger_info,
            status=Execution.Status.PENDING,
        )

        # Update pipeline last execution time
        pipeline.last_execution_at = timezone.now()
        pipeline.save(update_fields=['last_execution_at'])

        # TODO: Queue execution for processing (Celery task)

        return execution

    def _create_execution_for_pr(
        self,
        pipeline: Pipeline,
        config,
        event: PullRequestEvent,
        delivery_id: str
    ) -> Optional[Execution]:
        """Create an execution for a pull_request event."""
        # Get next execution number
        last_number = Execution.objects.filter(
            pipeline=pipeline
        ).order_by('-number').values_list('number', flat=True).first() or 0

        trigger_info = {
            'event_type': 'pull_request',
            'delivery_id': delivery_id,
            'action': event.action,
            'number': event.number,
            'title': event.title,
            'head_sha': event.head_sha,
            'head_branch': event.head_branch,
            'base_branch': event.base_branch,
            'head_repo': event.head_repo,
            'base_repo': event.base_repo,
            'is_fork': event.is_fork,
            'repository': event.repository.full_name if event.repository else '',
            'sender': event.sender.login if event.sender else '',
        }

        execution = Execution.objects.create(
            tenant=pipeline.tenant,
            pipeline=pipeline,
            pipeline_config=config,
            number=last_number + 1,
            trigger_type=Execution.TriggerType.PULL_REQUEST,
            trigger_info=trigger_info,
            status=Execution.Status.PENDING,
        )

        # Update pipeline last execution time
        pipeline.last_execution_at = timezone.now()
        pipeline.save(update_fields=['last_execution_at'])

        # TODO: Queue execution for processing (Celery task)

        return execution
