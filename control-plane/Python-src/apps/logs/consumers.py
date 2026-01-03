"""
Log WebSocket consumers for Muelsyse-CI
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async


class LogConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time log streaming.

    Clients can subscribe to:
    - /ws/logs/{execution_id}/ - All logs for an execution
    - /ws/logs/{execution_id}/{job_id}/ - Logs for a specific job
    """

    async def connect(self):
        self.execution_id = self.scope['url_route']['kwargs']['execution_id']
        self.job_id = self.scope['url_route']['kwargs'].get('job_id')

        # Determine group name
        if self.job_id:
            self.group_name = f'logs_job_{self.job_id}'
        else:
            self.group_name = f'logs_execution_{self.execution_id}'

        # Verify permissions
        if not await self.has_permission():
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'execution_id': self.execution_id,
            'job_id': self.job_id,
        }))

        # Send existing logs
        await self.send_history()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming messages from WebSocket."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except json.JSONDecodeError:
            pass

    async def log_message(self, event):
        """
        Receive log message from channel layer and send to WebSocket.
        """
        await self.send(text_data=json.dumps({
            'type': 'log',
            'job_id': event.get('job_id'),
            'step_id': event.get('step_id'),
            'timestamp': event.get('timestamp'),
            'content': event.get('content'),
            'level': event.get('level', 'info'),
        }))

    async def status_update(self, event):
        """
        Receive status update from channel layer and send to WebSocket.
        """
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'entity_type': event.get('entity_type'),
            'entity_id': event.get('entity_id'),
            'status': event.get('status'),
            'timestamp': event.get('timestamp'),
        }))

    @database_sync_to_async
    def has_permission(self):
        """Check if user has permission to view these logs."""
        from apps.executions.models import Execution

        # Get user from scope
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            return False

        try:
            execution = Execution.objects.get(id=self.execution_id)
            # Check tenant
            if hasattr(user, 'tenant') and execution.tenant != user.tenant:
                return False
            return True
        except Execution.DoesNotExist:
            return False

    @database_sync_to_async
    def get_existing_logs(self):
        """Fetch existing logs from database."""
        from apps.logs.models import LogChunk
        from apps.executions.models import Step

        if self.job_id:
            # Get logs for specific job
            steps = Step.objects.filter(job_id=self.job_id)
        else:
            # Get logs for entire execution
            from apps.executions.models import Job
            job_ids = Job.objects.filter(
                execution_id=self.execution_id
            ).values_list('id', flat=True)
            steps = Step.objects.filter(job_id__in=job_ids)

        step_ids = list(steps.values_list('id', flat=True))
        logs = LogChunk.objects.filter(
            step_id__in=step_ids
        ).order_by('step__job_id', 'step__order', 'chunk_number')[:1000]

        return [
            {
                'type': 'log',
                'job_id': str(log.step.job_id),
                'step_id': str(log.step_id),
                'timestamp': log.timestamp.isoformat(),
                'content': log.content,
                'level': log.level,
            }
            for log in logs
        ]

    async def send_history(self):
        """Send existing logs to newly connected client."""
        logs = await self.get_existing_logs()
        for log in logs:
            await self.send(text_data=json.dumps(log))

        # Send history complete marker
        await self.send(text_data=json.dumps({
            'type': 'history_complete',
            'count': len(logs),
        }))
