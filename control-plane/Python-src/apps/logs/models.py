"""
Log models for Muelsyse-CI

This module contains models for storing execution logs.
"""
from django.db import models


class LogChunk(models.Model):
    """
    Log chunk for step execution.

    Logs are stored in chunks for efficient streaming and retrieval.
    Each chunk represents a portion of the log output.
    """

    class Level(models.TextChoices):
        DEBUG = 'debug', 'Debug'
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        ERROR = 'error', 'Error'

    step = models.ForeignKey(
        'executions.Step',
        on_delete=models.CASCADE,
        related_name='log_chunks'
    )

    chunk_number = models.PositiveIntegerField()
    content = models.TextField()
    level = models.CharField(
        max_length=10,
        choices=Level.choices,
        default=Level.INFO
    )

    timestamp = models.DateTimeField()

    class Meta:
        ordering = ['chunk_number']
        unique_together = ['step', 'chunk_number']
        indexes = [
            models.Index(fields=['step', 'chunk_number']),
        ]

    def __str__(self):
        return f"{self.step} - Chunk {self.chunk_number}"


class LogBuffer:
    """
    In-memory buffer for log aggregation before database write.

    This is not a Django model but a utility class for batching log writes.
    """

    def __init__(self, flush_size: int = 100, flush_interval: float = 1.0):
        self.buffer = []
        self.flush_size = flush_size
        self.flush_interval = flush_interval
        self._last_flush = None

    def add(self, log_entry: dict) -> None:
        """Add a log entry to the buffer."""
        self.buffer.append(log_entry)
        if len(self.buffer) >= self.flush_size:
            self.flush()

    def flush(self) -> list:
        """Flush buffer to database and return flushed entries."""
        if not self.buffer:
            return []

        entries = self.buffer.copy()
        self.buffer.clear()

        # Bulk create log chunks
        LogChunk.objects.bulk_create([
            LogChunk(
                step_id=entry['step_id'],
                chunk_number=entry['chunk_number'],
                content=entry['content'],
                level=entry.get('level', 'info'),
                timestamp=entry['timestamp'],
            )
            for entry in entries
        ], ignore_conflicts=True)

        return entries
