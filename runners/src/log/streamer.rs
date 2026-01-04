//! Log streaming utilities with chunking, buffering, and sequence tracking
//!
//! Features:
//! - Log chunking for large log entries
//! - Buffered log queue with configurable size
//! - Sequence number tracking for reliable delivery
//! - Pending log persistence for reconnection retry
//! - Automatic flush on buffer full or timeout

use std::collections::{VecDeque, HashMap};
use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};
use chrono::{DateTime, Utc};
use tokio::sync::{mpsc, Mutex, RwLock};
use tracing::{debug, warn, info};
use anyhow::Result;

use crate::config::LoggingConfig;
use crate::client::{WebSocketClient, LogEntry as WsLogEntry};

// ============================================================================
// Log Entry Types
// ============================================================================

/// Log entry with sequence tracking
#[derive(Debug, Clone)]
pub struct LogEntry {
    /// Unique sequence number
    pub sequence: u64,
    /// Step ID
    pub step_id: String,
    /// Timestamp
    pub timestamp: DateTime<Utc>,
    /// Log content
    pub content: String,
    /// Log level (info, warn, error, debug)
    pub level: String,
    /// Whether this entry has been acknowledged
    pub acknowledged: bool,
}

impl LogEntry {
    /// Create a new log entry
    pub fn new(sequence: u64, step_id: String, content: String, level: String) -> Self {
        Self {
            sequence,
            step_id,
            timestamp: Utc::now(),
            content,
            level,
            acknowledged: false,
        }
    }

    /// Convert to WebSocket log entry format
    pub fn to_ws_entry(&self) -> WsLogEntry {
        WsLogEntry {
            step_id: self.step_id.clone(),
            timestamp: self.timestamp,
            content: self.content.clone(),
            level: self.level.clone(),
            sequence: self.sequence,
        }
    }
}

/// Log chunk for large log entries
#[derive(Debug, Clone)]
pub struct LogChunk {
    /// Original sequence number
    pub sequence: u64,
    /// Chunk index (0-based)
    pub chunk_index: usize,
    /// Total chunks
    pub total_chunks: usize,
    /// Chunk content
    pub content: String,
}

// ============================================================================
// Log Streamer
// ============================================================================

/// Enhanced log streamer with buffering and sequence tracking
pub struct LogStreamer {
    /// Job ID
    job_id: String,
    /// Configuration
    config: LoggingConfig,
    /// Sequence counter
    sequence_counter: AtomicU64,
    /// Pending logs (not yet acknowledged)
    pending: Arc<RwLock<VecDeque<LogEntry>>>,
    /// Last acknowledged sequence per step
    ack_sequences: Arc<RwLock<HashMap<String, u64>>>,
    /// Buffer for batching
    buffer: Arc<Mutex<VecDeque<LogEntry>>>,
    /// Last flush time
    last_flush: Arc<RwLock<Instant>>,
    /// WebSocket client reference
    ws_client: Option<Arc<WebSocketClient>>,
}

impl LogStreamer {
    /// Create a new log streamer for a job
    pub fn new(job_id: String, config: LoggingConfig) -> Self {
        Self {
            job_id,
            config,
            sequence_counter: AtomicU64::new(0),
            pending: Arc::new(RwLock::new(VecDeque::new())),
            ack_sequences: Arc::new(RwLock::new(HashMap::new())),
            buffer: Arc::new(Mutex::new(VecDeque::new())),
            last_flush: Arc::new(RwLock::new(Instant::now())),
            ws_client: None,
        }
    }

    /// Set WebSocket client for sending logs
    pub fn set_ws_client(&mut self, client: Arc<WebSocketClient>) {
        self.ws_client = Some(client);
    }

    /// Get next sequence number
    fn next_sequence(&self) -> u64 {
        self.sequence_counter.fetch_add(1, Ordering::SeqCst)
    }

    /// Add a log entry
    pub async fn add(&self, step_id: &str, content: &str, level: &str) -> Result<u64> {
        let sequence = self.next_sequence();

        // Check if content needs chunking
        if content.len() > self.config.chunk_size_bytes {
            self.add_chunked(step_id, content, level, sequence).await?;
        } else {
            let entry = LogEntry::new(
                sequence,
                step_id.to_string(),
                content.to_string(),
                level.to_string(),
            );
            self.add_entry(entry).await?;
        }

        Ok(sequence)
    }

    /// Add a chunked log entry (for large logs)
    async fn add_chunked(
        &self,
        step_id: &str,
        content: &str,
        level: &str,
        base_sequence: u64,
    ) -> Result<()> {
        let chunk_size = self.config.chunk_size_bytes;
        let chunks: Vec<&str> = content
            .as_bytes()
            .chunks(chunk_size)
            .map(|chunk| std::str::from_utf8(chunk).unwrap_or(""))
            .collect();

        let total_chunks = chunks.len();

        for (i, chunk_content) in chunks.into_iter().enumerate() {
            let chunk_marker = format!("[{}/{}] ", i + 1, total_chunks);
            let entry = LogEntry::new(
                base_sequence + i as u64,
                step_id.to_string(),
                format!("{}{}", chunk_marker, chunk_content),
                level.to_string(),
            );
            self.add_entry(entry).await?;
        }

        // Update sequence counter to account for extra chunks
        if total_chunks > 1 {
            self.sequence_counter.fetch_add((total_chunks - 1) as u64, Ordering::SeqCst);
        }

        Ok(())
    }

    /// Add a single log entry to buffer
    async fn add_entry(&self, entry: LogEntry) -> Result<()> {
        let mut buffer = self.buffer.lock().await;

        // Check buffer capacity
        if buffer.len() >= self.config.max_pending_logs {
            // Drop oldest unacknowledged log
            if let Some(dropped) = buffer.pop_front() {
                warn!(
                    "Log buffer full, dropping oldest entry: seq={}",
                    dropped.sequence
                );
            }
        }

        buffer.push_back(entry.clone());

        // Add to pending if persistence is enabled
        if self.config.enable_persistence {
            let mut pending = self.pending.write().await;
            pending.push_back(entry);
        }

        // Check if we should flush
        let should_flush = buffer.len() >= self.config.buffer_size;

        if should_flush {
            drop(buffer); // Release lock before flushing
            self.flush().await?;
        }

        Ok(())
    }

    /// Flush buffered logs to WebSocket
    pub async fn flush(&self) -> Result<()> {
        let entries: Vec<LogEntry> = {
            let mut buffer = self.buffer.lock().await;
            buffer.drain(..).collect()
        };

        if entries.is_empty() {
            return Ok(());
        }

        *self.last_flush.write().await = Instant::now();

        if let Some(ref ws) = self.ws_client {
            // Convert to WS format and send as batch
            let ws_entries: Vec<WsLogEntry> = entries
                .iter()
                .map(|e| e.to_ws_entry())
                .collect();

            debug!(
                "Flushing {} log entries for job {}",
                ws_entries.len(),
                self.job_id
            );

            ws.send_log_batch(&self.job_id, ws_entries).await?;
        } else {
            warn!("No WebSocket client set, logs not sent");
        }

        Ok(())
    }

    /// Flush if interval has elapsed
    pub async fn flush_if_needed(&self) -> Result<bool> {
        let last = *self.last_flush.read().await;
        let interval = Duration::from_millis(self.config.flush_interval_ms);

        if last.elapsed() >= interval {
            let buffer = self.buffer.lock().await;
            if !buffer.is_empty() {
                drop(buffer);
                self.flush().await?;
                return Ok(true);
            }
        }

        Ok(false)
    }

    /// Acknowledge logs up to a sequence number
    pub async fn acknowledge(&self, step_id: &str, last_sequence: u64) {
        // Update ack sequence for step
        {
            let mut ack_seqs = self.ack_sequences.write().await;
            ack_seqs.insert(step_id.to_string(), last_sequence);
        }

        // Remove acknowledged entries from pending
        if self.config.enable_persistence {
            let mut pending = self.pending.write().await;
            pending.retain(|e| {
                e.step_id != step_id || e.sequence > last_sequence
            });

            debug!(
                "Acknowledged logs up to seq={} for step {}, {} pending remaining",
                last_sequence,
                step_id,
                pending.len()
            );
        }
    }

    /// Get pending (unacknowledged) logs for retry
    pub async fn get_pending(&self) -> Vec<LogEntry> {
        let pending = self.pending.read().await;
        pending.iter().cloned().collect()
    }

    /// Resend pending logs (after reconnection)
    pub async fn resend_pending(&self) -> Result<usize> {
        let pending = self.get_pending().await;

        if pending.is_empty() {
            return Ok(0);
        }

        info!(
            "Resending {} pending log entries for job {}",
            pending.len(),
            self.job_id
        );

        if let Some(ref ws) = self.ws_client {
            let ws_entries: Vec<WsLogEntry> = pending
                .iter()
                .map(|e| e.to_ws_entry())
                .collect();

            ws.send_log_batch(&self.job_id, ws_entries).await?;
        }

        Ok(pending.len())
    }

    /// Get current buffer size
    pub async fn buffer_size(&self) -> usize {
        self.buffer.lock().await.len()
    }

    /// Get pending count
    pub async fn pending_count(&self) -> usize {
        self.pending.read().await.len()
    }

    /// Get current sequence number
    pub fn current_sequence(&self) -> u64 {
        self.sequence_counter.load(Ordering::SeqCst)
    }

    /// Clear all logs
    pub async fn clear(&self) {
        self.buffer.lock().await.clear();
        self.pending.write().await.clear();
        self.ack_sequences.write().await.clear();
    }
}

// ============================================================================
// Log Streamer Manager
// ============================================================================

/// Manager for multiple log streamers (one per job)
pub struct LogStreamerManager {
    config: LoggingConfig,
    streamers: Arc<RwLock<HashMap<String, Arc<LogStreamer>>>>,
}

impl LogStreamerManager {
    pub fn new(config: LoggingConfig) -> Self {
        Self {
            config,
            streamers: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Get or create a streamer for a job
    pub async fn get_or_create(&self, job_id: &str) -> Arc<LogStreamer> {
        let streamers = self.streamers.read().await;
        if let Some(streamer) = streamers.get(job_id) {
            return streamer.clone();
        }
        drop(streamers);

        let mut streamers = self.streamers.write().await;
        // Double-check after acquiring write lock
        if let Some(streamer) = streamers.get(job_id) {
            return streamer.clone();
        }

        let streamer = Arc::new(LogStreamer::new(
            job_id.to_string(),
            self.config.clone(),
        ));
        streamers.insert(job_id.to_string(), streamer.clone());
        streamer
    }

    /// Remove a streamer for a completed job
    pub async fn remove(&self, job_id: &str) -> Option<Arc<LogStreamer>> {
        let mut streamers = self.streamers.write().await;
        streamers.remove(job_id)
    }

    /// Flush all streamers
    pub async fn flush_all(&self) -> Result<()> {
        let streamers = self.streamers.read().await;
        for streamer in streamers.values() {
            streamer.flush().await?;
        }
        Ok(())
    }

    /// Get all job IDs with active streamers
    pub async fn active_jobs(&self) -> Vec<String> {
        let streamers = self.streamers.read().await;
        streamers.keys().cloned().collect()
    }
}

// ============================================================================
// Async Log Writer
// ============================================================================

/// Async log writer that processes logs in background
pub struct AsyncLogWriter {
    sender: mpsc::Sender<LogWriteRequest>,
}

/// Log write request
pub struct LogWriteRequest {
    pub job_id: String,
    pub step_id: String,
    pub content: String,
    pub level: String,
}

impl AsyncLogWriter {
    /// Create a new async log writer
    pub fn new(
        manager: Arc<LogStreamerManager>,
        buffer_size: usize,
    ) -> (Self, tokio::task::JoinHandle<()>) {
        let (tx, mut rx) = mpsc::channel::<LogWriteRequest>(buffer_size);

        let handle = tokio::spawn(async move {
            while let Some(req) = rx.recv().await {
                let streamer = manager.get_or_create(&req.job_id).await;
                if let Err(e) = streamer.add(&req.step_id, &req.content, &req.level).await {
                    warn!("Failed to add log entry: {}", e);
                }
            }
        });

        (Self { sender: tx }, handle)
    }

    /// Write a log entry asynchronously
    pub async fn write(
        &self,
        job_id: &str,
        step_id: &str,
        content: &str,
        level: &str,
    ) -> Result<()> {
        self.sender
            .send(LogWriteRequest {
                job_id: job_id.to_string(),
                step_id: step_id.to_string(),
                content: content.to_string(),
                level: level.to_string(),
            })
            .await
            .map_err(|_| anyhow::anyhow!("Log writer channel closed"))
    }

    /// Close the writer
    pub fn close(self) {
        drop(self.sender);
    }
}

// ============================================================================
// Legacy API Compatibility
// ============================================================================

/// Simple buffer for log entries (legacy compatibility)
pub struct SimpleLogBuffer {
    buffer: VecDeque<LogEntry>,
    flush_size: usize,
}

impl SimpleLogBuffer {
    pub fn new(flush_size: usize) -> Self {
        Self {
            buffer: VecDeque::new(),
            flush_size,
        }
    }

    /// Add a log entry
    pub fn add(&mut self, entry: LogEntry) {
        self.buffer.push_back(entry);
    }

    /// Check if buffer should be flushed
    pub fn should_flush(&self) -> bool {
        self.buffer.len() >= self.flush_size
    }

    /// Drain all entries from buffer
    pub fn drain(&mut self) -> Vec<LogEntry> {
        self.buffer.drain(..).collect()
    }

    /// Get buffer size
    pub fn len(&self) -> usize {
        self.buffer.len()
    }

    /// Check if buffer is empty
    pub fn is_empty(&self) -> bool {
        self.buffer.is_empty()
    }
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    fn test_config() -> LoggingConfig {
        LoggingConfig {
            buffer_size: 10,
            chunk_size_bytes: 100,
            flush_interval_ms: 1000,
            enable_persistence: true,
            max_pending_logs: 1000,
        }
    }

    #[tokio::test]
    async fn test_log_entry_creation() {
        let entry = LogEntry::new(
            1,
            "step-1".to_string(),
            "Test log".to_string(),
            "info".to_string(),
        );

        assert_eq!(entry.sequence, 1);
        assert_eq!(entry.step_id, "step-1");
        assert_eq!(entry.content, "Test log");
        assert_eq!(entry.level, "info");
        assert!(!entry.acknowledged);
    }

    #[tokio::test]
    async fn test_streamer_sequence() {
        let streamer = LogStreamer::new("job-1".to_string(), test_config());

        let seq1 = streamer.add("step-1", "Log 1", "info").await.unwrap();
        let seq2 = streamer.add("step-1", "Log 2", "info").await.unwrap();
        let seq3 = streamer.add("step-1", "Log 3", "info").await.unwrap();

        assert_eq!(seq1, 0);
        assert_eq!(seq2, 1);
        assert_eq!(seq3, 2);
        assert_eq!(streamer.current_sequence(), 3);
    }

    #[tokio::test]
    async fn test_streamer_acknowledgment() {
        let streamer = LogStreamer::new("job-1".to_string(), test_config());

        // Add some logs
        streamer.add("step-1", "Log 1", "info").await.unwrap();
        streamer.add("step-1", "Log 2", "info").await.unwrap();
        streamer.add("step-1", "Log 3", "info").await.unwrap();

        assert_eq!(streamer.pending_count().await, 3);

        // Acknowledge first two
        streamer.acknowledge("step-1", 1).await;

        assert_eq!(streamer.pending_count().await, 1);
    }

    #[tokio::test]
    async fn test_chunking() {
        let config = LoggingConfig {
            buffer_size: 100,
            chunk_size_bytes: 10,
            flush_interval_ms: 1000,
            enable_persistence: true,
            max_pending_logs: 1000,
        };

        let streamer = LogStreamer::new("job-1".to_string(), config);

        // Add a log that needs chunking (25 bytes)
        let long_log = "1234567890123456789012345";
        streamer.add("step-1", long_log, "info").await.unwrap();

        // Should have created 3 chunks
        assert_eq!(streamer.pending_count().await, 3);
    }

    #[tokio::test]
    async fn test_manager() {
        let config = test_config();
        let manager = LogStreamerManager::new(config);

        let s1 = manager.get_or_create("job-1").await;
        let s2 = manager.get_or_create("job-2").await;
        let s1_again = manager.get_or_create("job-1").await;

        // Same job should return same streamer
        assert!(Arc::ptr_eq(&s1, &s1_again));
        assert!(!Arc::ptr_eq(&s1, &s2));

        let jobs = manager.active_jobs().await;
        assert_eq!(jobs.len(), 2);
    }
}
