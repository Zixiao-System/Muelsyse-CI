"""
Runner WebSocket consumer for Muelsyse-CI

Handles bidirectional communication between runners and control plane.
"""
import json
import hashlib
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from asgiref.sync import sync_to_async


class RunnerConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for runner communication.

    Protocol:
    - Runner connects with token in query string
    - Runner sends heartbeats and job status updates
    - Control plane sends job assignments and cancellations
    """

    async def connect(self):
        self.runner_id = self.scope['url_route']['kwargs']['runner_id']
        self.runner = None
        self.group_name = f'runner_{self.runner_id}'

        # Authenticate runner
        if not await self.authenticate():
            await self.close()
            return

        # Join runner-specific group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Also join tenant group for broadcasts
        if self.runner.tenant_id:
            await self.channel_layer.group_add(
                f'runners_tenant_{self.runner.tenant_id}',
                self.channel_name
            )

        await self.accept()

        # Mark runner as online
        await self.set_runner_online()

        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'runner_id': self.runner_id,
        }))

    async def disconnect(self, close_code):
        # Mark runner as offline
        await self.set_runner_offline()

        # Leave groups
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

        if self.runner and self.runner.tenant_id:
            await self.channel_layer.group_discard(
                f'runners_tenant_{self.runner.tenant_id}',
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming messages from runner."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            handlers = {
                'heartbeat': self.handle_heartbeat,
                'log': self.handle_log,
                'status_update': self.handle_status_update,
                'job_complete': self.handle_job_complete,
                'artifact_ready': self.handle_artifact_ready,
            }

            handler = handlers.get(message_type)
            if handler:
                await handler(data)
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))

    # Outgoing message handlers (from control plane to runner)

    async def job_assignment(self, event):
        """Send job assignment to runner."""
        await self.send(text_data=json.dumps({
            'type': 'job_assignment',
            'job': event['job'],
        }))

    async def job_cancel(self, event):
        """Send job cancellation to runner."""
        await self.send(text_data=json.dumps({
            'type': 'job_cancel',
            'job_id': event['job_id'],
        }))

    # Incoming message handlers (from runner to control plane)

    async def handle_heartbeat(self, data):
        """Handle heartbeat from runner."""
        system_info = data.get('system_info', {})
        current_jobs = data.get('current_jobs', 0)

        await self.update_runner_heartbeat(system_info, current_jobs)

        await self.send(text_data=json.dumps({
            'type': 'heartbeat_ack',
            'timestamp': timezone.now().isoformat(),
        }))

    async def handle_log(self, data):
        """Handle log message from runner."""
        from channels.layers import get_channel_layer

        job_id = data.get('job_id')
        step_id = data.get('step_id')
        content = data.get('content')
        level = data.get('level', 'info')
        timestamp = data.get('timestamp', timezone.now().isoformat())

        # Store log
        await self.store_log(step_id, content, level, timestamp)

        # Broadcast to log subscribers
        channel_layer = get_channel_layer()

        # Get execution_id for the job
        execution_id = await self.get_execution_id(job_id)

        # Send to job-specific group
        await channel_layer.group_send(
            f'logs_job_{job_id}',
            {
                'type': 'log_message',
                'job_id': job_id,
                'step_id': step_id,
                'content': content,
                'level': level,
                'timestamp': timestamp,
            }
        )

        # Send to execution group
        if execution_id:
            await channel_layer.group_send(
                f'logs_execution_{execution_id}',
                {
                    'type': 'log_message',
                    'job_id': job_id,
                    'step_id': step_id,
                    'content': content,
                    'level': level,
                    'timestamp': timestamp,
                }
            )

    async def handle_status_update(self, data):
        """Handle status update from runner."""
        entity_type = data.get('entity_type')  # 'job' or 'step'
        entity_id = data.get('entity_id')
        new_status = data.get('status')
        exit_code = data.get('exit_code')
        outputs = data.get('outputs', {})

        await self.update_entity_status(
            entity_type, entity_id, new_status, exit_code, outputs
        )

        # Broadcast status update
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()

        if entity_type == 'job':
            execution_id = await self.get_execution_id(entity_id)
            if execution_id:
                await channel_layer.group_send(
                    f'logs_execution_{execution_id}',
                    {
                        'type': 'status_update',
                        'entity_type': entity_type,
                        'entity_id': entity_id,
                        'status': new_status,
                        'timestamp': timezone.now().isoformat(),
                    }
                )

    async def handle_job_complete(self, data):
        """Handle job completion from runner."""
        job_id = data.get('job_id')
        status = data.get('status')
        outputs = data.get('outputs', {})

        await self.complete_job(job_id, status, outputs)

        # Decrement current jobs count
        await self.decrement_runner_jobs()

    async def handle_artifact_ready(self, data):
        """Handle artifact upload notification from runner."""
        job_id = data.get('job_id')
        artifact_name = data.get('artifact_name')
        artifact_path = data.get('artifact_path')
        size_bytes = data.get('size_bytes')
        checksum = data.get('checksum')

        await self.create_artifact(
            job_id, artifact_name, artifact_path, size_bytes, checksum
        )

    # Database operations

    @database_sync_to_async
    def authenticate(self):
        """Authenticate runner using token from query string."""
        from apps.runners.models import Runner

        query_string = self.scope.get('query_string', b'').decode()
        params = dict(p.split('=') for p in query_string.split('&') if '=' in p)
        token = params.get('token', '')

        if not token:
            return False

        token_hash = hashlib.sha256(token.encode()).hexdigest()

        try:
            self.runner = Runner.objects.get(
                id=self.runner_id,
                token_hash=token_hash
            )
            return True
        except Runner.DoesNotExist:
            return False

    @database_sync_to_async
    def set_runner_online(self):
        from apps.runners.models import Runner
        Runner.objects.filter(id=self.runner_id).update(
            status=Runner.Status.ONLINE,
            last_heartbeat=timezone.now()
        )

    @database_sync_to_async
    def set_runner_offline(self):
        from apps.runners.models import Runner
        Runner.objects.filter(id=self.runner_id).update(
            status=Runner.Status.OFFLINE
        )

    @database_sync_to_async
    def update_runner_heartbeat(self, system_info, current_jobs):
        from apps.runners.models import Runner
        Runner.objects.filter(id=self.runner_id).update(
            last_heartbeat=timezone.now(),
            system_info=system_info,
            current_jobs=current_jobs
        )

    @database_sync_to_async
    def store_log(self, step_id, content, level, timestamp):
        from apps.logs.models import LogChunk
        from apps.executions.models import Step
        from django.utils.dateparse import parse_datetime

        try:
            step = Step.objects.get(id=step_id)
            last_chunk = step.log_chunks.order_by('-chunk_number').first()
            next_chunk = (last_chunk.chunk_number + 1) if last_chunk else 0

            LogChunk.objects.create(
                step=step,
                chunk_number=next_chunk,
                content=content,
                level=level,
                timestamp=parse_datetime(timestamp) or timezone.now()
            )
        except Step.DoesNotExist:
            pass

    @database_sync_to_async
    def get_execution_id(self, job_id):
        from apps.executions.models import Job
        try:
            job = Job.objects.get(id=job_id)
            return str(job.execution_id)
        except Job.DoesNotExist:
            return None

    @database_sync_to_async
    def update_entity_status(self, entity_type, entity_id, status, exit_code, outputs):
        if entity_type == 'job':
            from apps.executions.models import Job
            update_fields = {'status': status}
            if status == 'running':
                update_fields['started_at'] = timezone.now()
            elif status in ('success', 'failed', 'cancelled', 'timeout'):
                update_fields['finished_at'] = timezone.now()
                update_fields['outputs'] = outputs
            Job.objects.filter(id=entity_id).update(**update_fields)

        elif entity_type == 'step':
            from apps.executions.models import Step
            update_fields = {'status': status}
            if exit_code is not None:
                update_fields['exit_code'] = exit_code
            if status == 'running':
                update_fields['started_at'] = timezone.now()
            elif status in ('success', 'failed', 'cancelled', 'timeout', 'skipped'):
                update_fields['finished_at'] = timezone.now()
                update_fields['outputs'] = outputs
            Step.objects.filter(id=entity_id).update(**update_fields)

    @database_sync_to_async
    def complete_job(self, job_id, status, outputs):
        from apps.executions.models import Job
        Job.objects.filter(id=job_id).update(
            status=status,
            finished_at=timezone.now(),
            outputs=outputs
        )

    @database_sync_to_async
    def decrement_runner_jobs(self):
        from apps.runners.models import Runner
        from django.db.models import F
        Runner.objects.filter(id=self.runner_id).update(
            current_jobs=F('current_jobs') - 1
        )

    @database_sync_to_async
    def create_artifact(self, job_id, name, path, size_bytes, checksum):
        from apps.artifacts.models import Artifact
        from apps.executions.models import Job

        try:
            job = Job.objects.select_related('execution').get(id=job_id)
            Artifact.objects.create(
                tenant=job.execution.tenant,
                execution=job.execution,
                job=job,
                name=name,
                storage_path=path,
                size_bytes=size_bytes,
                checksum_sha256=checksum,
            )
        except Job.DoesNotExist:
            pass
