//! Log streaming utilities

use std::collections::VecDeque;
use chrono::{DateTime, Utc};

/// Log entry
#[derive(Debug, Clone)]
pub struct LogEntry {
    pub step_id: String,
    pub timestamp: DateTime<Utc>,
    pub content: String,
    pub level: String,
}

/// Buffer for log entries before sending
pub struct LogStreamer {
    buffer: VecDeque<LogEntry>,
    flush_size: usize,
}

impl LogStreamer {
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
