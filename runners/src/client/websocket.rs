//! WebSocket client for control plane communication
//!
//! Features:
//! - Exponential backoff reconnection
//! - Ping/pong heartbeat
//! - Connection state callbacks
//! - Automatic reconnection on disconnect

use anyhow::Result;
use futures_util::{SinkExt, StreamExt};
use tokio_tungstenite::{connect_async, tungstenite::Message as WsMessage};
use serde::{Serialize, Deserialize};
use tracing::{info, warn, debug, error};
use chrono::{DateTime, Utc};
use std::collections::HashMap;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant};
use tokio::sync::{mpsc, Mutex, RwLock};

use crate::config::{Settings, WebSocketConfig};

// ============================================================================
// Connection State
// ============================================================================

/// Connection state enum
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConnectionState {
    Disconnected,
    Connecting,
    Connected,
    Reconnecting,
    Failed,
}

impl std::fmt::Display for ConnectionState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Disconnected => write!(f, "disconnected"),
            Self::Connecting => write!(f, "connecting"),
            Self::Connected => write!(f, "connected"),
            Self::Reconnecting => write!(f, "reconnecting"),
            Self::Failed => write!(f, "failed"),
        }
    }
}

/// Callback for connection state changes
pub type StateCallback = Arc<dyn Fn(ConnectionState) + Send + Sync>;

// ============================================================================
// Reconnection Strategy
// ============================================================================

/// Exponential backoff reconnection strategy
#[derive(Debug, Clone)]
pub struct ReconnectStrategy {
    /// Initial delay in milliseconds
    initial_delay_ms: u64,
    /// Maximum delay in milliseconds
    max_delay_ms: u64,
    /// Backoff multiplier
    multiplier: f64,
    /// Maximum attempts (0 = unlimited)
    max_attempts: u32,
    /// Current attempt count
    current_attempt: u32,
    /// Current delay
    current_delay_ms: u64,
}

impl ReconnectStrategy {
    pub fn new(config: &WebSocketConfig) -> Self {
        Self {
            initial_delay_ms: config.reconnect_initial_delay_ms,
            max_delay_ms: config.reconnect_max_delay_ms,
            multiplier: config.reconnect_multiplier,
            max_attempts: config.max_reconnect_attempts,
            current_attempt: 0,
            current_delay_ms: config.reconnect_initial_delay_ms,
        }
    }

    /// Get next delay, returns None if max attempts reached
    pub fn next_delay(&mut self) -> Option<Duration> {
        if self.max_attempts > 0 && self.current_attempt >= self.max_attempts {
            return None;
        }

        let delay = Duration::from_millis(self.current_delay_ms);

        // Update for next iteration
        self.current_attempt += 1;
        self.current_delay_ms = std::cmp::min(
            (self.current_delay_ms as f64 * self.multiplier) as u64,
            self.max_delay_ms,
        );

        Some(delay)
    }

    /// Reset the strategy after successful connection
    pub fn reset(&mut self) {
        self.current_attempt = 0;
        self.current_delay_ms = self.initial_delay_ms;
    }

    /// Get current attempt count
    pub fn attempts(&self) -> u32 {
        self.current_attempt
    }
}

// ============================================================================
// Messages
// ============================================================================

/// Messages sent from runner to control plane
#[derive(Debug, Clone, Serialize)]
#[serde(tag = "type")]
pub enum OutgoingMessage {
    #[serde(rename = "heartbeat")]
    Heartbeat {
        runner_id: String,
        status: String,
        current_jobs: u32,
        system_info: SystemInfo,
    },

    #[serde(rename = "log")]
    Log {
        job_id: String,
        step_id: String,
        timestamp: DateTime<Utc>,
        content: String,
        level: String,
        #[serde(skip_serializing_if = "Option::is_none")]
        sequence: Option<u64>,
    },

    #[serde(rename = "log_batch")]
    LogBatch {
        job_id: String,
        logs: Vec<LogEntry>,
    },

    #[serde(rename = "status_update")]
    StatusUpdate {
        entity_type: String,
        entity_id: String,
        status: String,
        exit_code: Option<i32>,
        outputs: HashMap<String, String>,
    },

    #[serde(rename = "job_complete")]
    JobComplete {
        job_id: String,
        status: String,
        outputs: HashMap<String, String>,
    },

    #[serde(rename = "artifact_ready")]
    ArtifactReady {
        job_id: String,
        artifact_name: String,
        artifact_path: String,
        size_bytes: u64,
        checksum: String,
    },

    #[serde(rename = "runner_offline")]
    RunnerOffline {
        runner_id: String,
        reason: String,
    },
}

/// Log entry for batch sending
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogEntry {
    pub step_id: String,
    pub timestamp: DateTime<Utc>,
    pub content: String,
    pub level: String,
    pub sequence: u64,
}

/// Messages received from control plane
#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "type")]
pub enum IncomingMessage {
    #[serde(rename = "connected")]
    Connected { runner_id: String },

    #[serde(rename = "heartbeat_ack")]
    HeartbeatAck { timestamp: String },

    #[serde(rename = "job_assignment")]
    JobAssignment { job: JobSpec },

    #[serde(rename = "job_cancel")]
    JobCancel { job_id: String },

    #[serde(rename = "log_ack")]
    LogAck {
        job_id: String,
        last_sequence: u64,
    },

    #[serde(rename = "error")]
    Error { message: String },

    #[serde(rename = "pong")]
    Pong { timestamp: i64 },
}

/// System information for heartbeat
#[derive(Debug, Clone, Serialize)]
pub struct SystemInfo {
    pub os: String,
    pub arch: String,
    pub cpu_count: usize,
    pub cpu_usage_percent: f32,
    pub memory_total_mb: u64,
    pub memory_used_mb: u64,
    pub memory_usage_percent: f32,
}

/// Job specification received from control plane
#[derive(Debug, Clone, Deserialize)]
pub struct JobSpec {
    pub job_id: String,
    pub execution_id: String,
    pub name: String,
    pub steps: Vec<StepSpec>,
    pub environment: HashMap<String, String>,
    pub secrets: HashMap<String, String>,
    pub container: Option<ContainerSpec>,
    pub timeout_minutes: u32,
    pub workspace: WorkspaceSpec,
}

/// Step specification
#[derive(Debug, Clone, Deserialize)]
pub struct StepSpec {
    pub step_id: String,
    pub name: String,
    pub run: Option<String>,
    pub uses: Option<String>,
    #[serde(default)]
    pub with_inputs: HashMap<String, serde_json::Value>,
    #[serde(default)]
    pub env: HashMap<String, String>,
    pub working_directory: Option<String>,
    #[serde(default = "default_shell")]
    pub shell: String,
    #[serde(default)]
    pub continue_on_error: bool,
    #[serde(default = "default_timeout")]
    pub timeout_minutes: u32,
}

/// Container specification
#[derive(Debug, Clone, Deserialize)]
pub struct ContainerSpec {
    pub image: String,
    #[serde(default)]
    pub env: HashMap<String, String>,
    #[serde(default)]
    pub volumes: Vec<String>,
    pub options: Option<String>,
}

/// Workspace specification
#[derive(Debug, Clone, Deserialize)]
pub struct WorkspaceSpec {
    pub path: String,
    pub repository_url: Option<String>,
    pub commit_sha: Option<String>,
    pub branch: Option<String>,
}

fn default_shell() -> String { "bash".into() }
fn default_timeout() -> u32 { 60 }

// ============================================================================
// WebSocket Client
// ============================================================================

/// Type alias for the WebSocket stream
type WsStream = tokio_tungstenite::WebSocketStream<
    tokio_tungstenite::MaybeTlsStream<tokio::net::TcpStream>
>;

/// Enhanced WebSocket client with reconnection and heartbeat support
pub struct WebSocketClient {
    settings: Settings,
    state: Arc<RwLock<ConnectionState>>,
    is_running: Arc<AtomicBool>,
    last_pong: Arc<RwLock<Instant>>,
    message_tx: mpsc::Sender<OutgoingMessage>,
    message_rx: Arc<Mutex<mpsc::Receiver<IncomingMessage>>>,
    state_callbacks: Arc<RwLock<Vec<StateCallback>>>,
    reconnect_strategy: Arc<Mutex<ReconnectStrategy>>,
}

impl WebSocketClient {
    /// Create a new WebSocket client and start connection
    pub async fn new(settings: Settings) -> Result<Self> {
        let (outgoing_tx, outgoing_rx) = mpsc::channel::<OutgoingMessage>(1000);
        let (incoming_tx, incoming_rx) = mpsc::channel::<IncomingMessage>(1000);

        let state = Arc::new(RwLock::new(ConnectionState::Disconnected));
        let is_running = Arc::new(AtomicBool::new(true));
        let last_pong = Arc::new(RwLock::new(Instant::now()));
        let state_callbacks: Arc<RwLock<Vec<StateCallback>>> = Arc::new(RwLock::new(Vec::new()));
        let reconnect_strategy = Arc::new(Mutex::new(ReconnectStrategy::new(&settings.websocket)));

        let client = Self {
            settings: settings.clone(),
            state: state.clone(),
            is_running: is_running.clone(),
            last_pong: last_pong.clone(),
            message_tx: outgoing_tx,
            message_rx: Arc::new(Mutex::new(incoming_rx)),
            state_callbacks: state_callbacks.clone(),
            reconnect_strategy: reconnect_strategy.clone(),
        };

        // Spawn connection management task
        let settings_clone = settings.clone();
        let outgoing_rx = Arc::new(Mutex::new(outgoing_rx));

        tokio::spawn(async move {
            Self::connection_loop(
                settings_clone,
                state,
                is_running,
                last_pong,
                outgoing_rx,
                incoming_tx,
                state_callbacks,
                reconnect_strategy,
            ).await;
        });

        Ok(client)
    }

    /// Legacy connect method for backward compatibility
    pub async fn connect(settings: Settings) -> Result<Self> {
        Self::new(settings).await
    }

    /// Main connection loop with reconnection logic
    async fn connection_loop(
        settings: Settings,
        state: Arc<RwLock<ConnectionState>>,
        is_running: Arc<AtomicBool>,
        last_pong: Arc<RwLock<Instant>>,
        outgoing_rx: Arc<Mutex<mpsc::Receiver<OutgoingMessage>>>,
        incoming_tx: mpsc::Sender<IncomingMessage>,
        state_callbacks: Arc<RwLock<Vec<StateCallback>>>,
        reconnect_strategy: Arc<Mutex<ReconnectStrategy>>,
    ) {
        while is_running.load(Ordering::SeqCst) {
            // Update state
            Self::set_state(&state, &state_callbacks, ConnectionState::Connecting).await;

            let url = format!(
                "{}/ws/runner/{}/?token={}",
                settings.control_plane.ws_url,
                settings.runner.id,
                settings.runner.token
            );

            info!("Connecting to control plane: {}", settings.control_plane.ws_url);

            match connect_async(&url).await {
                Ok((ws_stream, _)) => {
                    info!("WebSocket connected successfully");
                    Self::set_state(&state, &state_callbacks, ConnectionState::Connected).await;

                    // Reset reconnect strategy on successful connection
                    reconnect_strategy.lock().await.reset();

                    // Reset last pong time
                    *last_pong.write().await = Instant::now();

                    // Handle the connection
                    if let Err(e) = Self::handle_connection(
                        ws_stream,
                        &settings,
                        &is_running,
                        &last_pong,
                        &outgoing_rx,
                        &incoming_tx,
                    ).await {
                        warn!("Connection error: {}", e);
                    }
                }
                Err(e) => {
                    error!("Failed to connect: {}", e);
                }
            }

            // Check if we should continue
            if !is_running.load(Ordering::SeqCst) {
                break;
            }

            // Get next reconnect delay
            let delay = {
                let mut strategy = reconnect_strategy.lock().await;
                match strategy.next_delay() {
                    Some(d) => {
                        info!(
                            "Reconnecting in {:?} (attempt {})",
                            d,
                            strategy.attempts()
                        );
                        d
                    }
                    None => {
                        error!("Max reconnection attempts reached");
                        Self::set_state(&state, &state_callbacks, ConnectionState::Failed).await;
                        break;
                    }
                }
            };

            Self::set_state(&state, &state_callbacks, ConnectionState::Reconnecting).await;
            tokio::time::sleep(delay).await;
        }

        Self::set_state(&state, &state_callbacks, ConnectionState::Disconnected).await;
        info!("WebSocket connection loop ended");
    }

    /// Handle an active WebSocket connection
    async fn handle_connection(
        ws_stream: WsStream,
        settings: &Settings,
        is_running: &Arc<AtomicBool>,
        last_pong: &Arc<RwLock<Instant>>,
        outgoing_rx: &Arc<Mutex<mpsc::Receiver<OutgoingMessage>>>,
        incoming_tx: &mpsc::Sender<IncomingMessage>,
    ) -> Result<()> {
        let (mut sender, mut receiver) = ws_stream.split();

        let heartbeat_interval = Duration::from_secs(settings.websocket.heartbeat_interval_secs);
        let heartbeat_timeout = Duration::from_secs(settings.websocket.heartbeat_timeout_secs);
        let enable_heartbeat = settings.websocket.enable_heartbeat;

        let mut heartbeat_timer = tokio::time::interval(heartbeat_interval);
        heartbeat_timer.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Delay);

        loop {
            tokio::select! {
                // Check for incoming messages
                msg = receiver.next() => {
                    match msg {
                        Some(Ok(WsMessage::Text(text))) => {
                            debug!("Received: {}", text);
                            match serde_json::from_str::<IncomingMessage>(&text) {
                                Ok(message) => {
                                    // Update pong time for any message
                                    *last_pong.write().await = Instant::now();

                                    if incoming_tx.send(message).await.is_err() {
                                        warn!("Failed to forward incoming message");
                                    }
                                }
                                Err(e) => {
                                    warn!("Failed to parse message: {} - {}", e, text);
                                }
                            }
                        }
                        Some(Ok(WsMessage::Ping(data))) => {
                            debug!("Received ping, sending pong");
                            sender.send(WsMessage::Pong(data)).await?;
                            *last_pong.write().await = Instant::now();
                        }
                        Some(Ok(WsMessage::Pong(_))) => {
                            debug!("Received pong");
                            *last_pong.write().await = Instant::now();
                        }
                        Some(Ok(WsMessage::Close(frame))) => {
                            info!("WebSocket closed by server: {:?}", frame);
                            return Ok(());
                        }
                        Some(Ok(_)) => {}
                        Some(Err(e)) => {
                            warn!("WebSocket error: {}", e);
                            return Err(e.into());
                        }
                        None => {
                            info!("WebSocket stream ended");
                            return Ok(());
                        }
                    }
                }

                // Check for outgoing messages
                msg = async {
                    outgoing_rx.lock().await.recv().await
                } => {
                    if let Some(message) = msg {
                        let json = serde_json::to_string(&message)?;
                        debug!("Sending: {}", json);
                        sender.send(WsMessage::Text(json)).await?;
                    }
                }

                // Heartbeat timer
                _ = heartbeat_timer.tick(), if enable_heartbeat => {
                    // Check if we've received a pong recently
                    let last = *last_pong.read().await;
                    if last.elapsed() > heartbeat_timeout {
                        warn!("Heartbeat timeout, reconnecting...");
                        return Err(anyhow::anyhow!("Heartbeat timeout"));
                    }

                    // Send ping
                    debug!("Sending ping");
                    let ping_data = Utc::now().timestamp_millis().to_be_bytes().to_vec();
                    sender.send(WsMessage::Ping(ping_data)).await?;
                }

                // Check if we should stop
                _ = tokio::time::sleep(Duration::from_millis(100)) => {
                    if !is_running.load(Ordering::SeqCst) {
                        info!("Shutting down connection");
                        let _ = sender.close().await;
                        return Ok(());
                    }
                }
            }
        }
    }

    /// Set connection state and notify callbacks
    async fn set_state(
        state: &Arc<RwLock<ConnectionState>>,
        callbacks: &Arc<RwLock<Vec<StateCallback>>>,
        new_state: ConnectionState,
    ) {
        let old_state = {
            let mut s = state.write().await;
            let old = *s;
            *s = new_state;
            old
        };

        if old_state != new_state {
            info!("Connection state: {} -> {}", old_state, new_state);

            let callbacks = callbacks.read().await;
            for callback in callbacks.iter() {
                callback(new_state);
            }
        }
    }

    /// Register a state change callback
    pub async fn on_state_change(&self, callback: StateCallback) {
        self.state_callbacks.write().await.push(callback);
    }

    /// Get current connection state
    pub async fn state(&self) -> ConnectionState {
        *self.state.read().await
    }

    /// Check if connected
    pub async fn is_connected(&self) -> bool {
        *self.state.read().await == ConnectionState::Connected
    }

    /// Send a message (queued for sending)
    pub async fn send(&self, message: &OutgoingMessage) -> Result<()> {
        self.message_tx.send(message.clone())
            .await
            .map_err(|_| anyhow::anyhow!("Failed to queue message for sending"))
    }

    /// Receive a message (blocking)
    pub async fn receive(&self) -> Result<Option<IncomingMessage>> {
        let mut rx = self.message_rx.lock().await;
        match rx.recv().await {
            Some(msg) => Ok(Some(msg)),
            None => Ok(None),
        }
    }

    /// Try to receive a message (non-blocking)
    pub async fn try_receive(&self) -> Option<IncomingMessage> {
        let mut rx = self.message_rx.lock().await;
        rx.try_recv().ok()
    }

    /// Send heartbeat
    pub async fn send_heartbeat(
        &self,
        runner_id: &str,
        current_jobs: u32,
    ) -> Result<()> {
        let system_info = get_system_info();

        self.send(&OutgoingMessage::Heartbeat {
            runner_id: runner_id.to_string(),
            status: if current_jobs > 0 { "busy" } else { "online" }.to_string(),
            current_jobs,
            system_info,
        }).await
    }

    /// Send log entry
    pub async fn send_log(
        &self,
        job_id: &str,
        step_id: &str,
        content: &str,
        level: &str,
    ) -> Result<()> {
        self.send(&OutgoingMessage::Log {
            job_id: job_id.to_string(),
            step_id: step_id.to_string(),
            timestamp: Utc::now(),
            content: content.to_string(),
            level: level.to_string(),
            sequence: None,
        }).await
    }

    /// Send log entry with sequence number
    pub async fn send_log_with_sequence(
        &self,
        job_id: &str,
        step_id: &str,
        content: &str,
        level: &str,
        sequence: u64,
    ) -> Result<()> {
        self.send(&OutgoingMessage::Log {
            job_id: job_id.to_string(),
            step_id: step_id.to_string(),
            timestamp: Utc::now(),
            content: content.to_string(),
            level: level.to_string(),
            sequence: Some(sequence),
        }).await
    }

    /// Send log batch
    pub async fn send_log_batch(
        &self,
        job_id: &str,
        logs: Vec<LogEntry>,
    ) -> Result<()> {
        self.send(&OutgoingMessage::LogBatch {
            job_id: job_id.to_string(),
            logs,
        }).await
    }

    /// Send status update
    pub async fn send_status_update(
        &self,
        entity_type: &str,
        entity_id: &str,
        status: &str,
        exit_code: Option<i32>,
        outputs: HashMap<String, String>,
    ) -> Result<()> {
        self.send(&OutgoingMessage::StatusUpdate {
            entity_type: entity_type.to_string(),
            entity_id: entity_id.to_string(),
            status: status.to_string(),
            exit_code,
            outputs,
        }).await
    }

    /// Send runner offline notification
    pub async fn send_offline_notification(&self, runner_id: &str, reason: &str) -> Result<()> {
        self.send(&OutgoingMessage::RunnerOffline {
            runner_id: runner_id.to_string(),
            reason: reason.to_string(),
        }).await
    }

    /// Close connection gracefully
    pub async fn close(&self) -> Result<()> {
        self.is_running.store(false, Ordering::SeqCst);
        Ok(())
    }

    /// Wait for connection to be established
    pub async fn wait_connected(&self, timeout: Duration) -> Result<()> {
        let start = Instant::now();
        while start.elapsed() < timeout {
            if self.is_connected().await {
                return Ok(());
            }
            tokio::time::sleep(Duration::from_millis(100)).await;
        }
        Err(anyhow::anyhow!("Connection timeout"))
    }
}

/// Get current system information
fn get_system_info() -> SystemInfo {
    use sysinfo::System;

    let mut sys = System::new_all();
    sys.refresh_all();

    // sysinfo 0.30 uses global_cpu_info() instead of global_cpu_usage()
    let cpu_usage = sys.global_cpu_info().cpu_usage();
    let total_memory = sys.total_memory() / 1024 / 1024;
    let used_memory = sys.used_memory() / 1024 / 1024;

    SystemInfo {
        os: System::name().unwrap_or_else(|| "unknown".into()),
        arch: std::env::consts::ARCH.to_string(),
        cpu_count: sys.cpus().len(),
        cpu_usage_percent: cpu_usage,
        memory_total_mb: total_memory,
        memory_used_mb: used_memory,
        memory_usage_percent: if total_memory > 0 {
            (used_memory as f32 / total_memory as f32) * 100.0
        } else {
            0.0
        },
    }
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_reconnect_strategy() {
        let config = WebSocketConfig {
            reconnect_initial_delay_ms: 1000,
            reconnect_max_delay_ms: 60000,
            reconnect_multiplier: 2.0,
            max_reconnect_attempts: 5,
            heartbeat_interval_secs: 30,
            heartbeat_timeout_secs: 10,
            enable_heartbeat: true,
        };

        let mut strategy = ReconnectStrategy::new(&config);

        // First delay should be 1000ms
        assert_eq!(strategy.next_delay(), Some(Duration::from_millis(1000)));
        assert_eq!(strategy.attempts(), 1);

        // Second delay should be 2000ms
        assert_eq!(strategy.next_delay(), Some(Duration::from_millis(2000)));
        assert_eq!(strategy.attempts(), 2);

        // Third delay should be 4000ms
        assert_eq!(strategy.next_delay(), Some(Duration::from_millis(4000)));

        // Fourth delay should be 8000ms
        assert_eq!(strategy.next_delay(), Some(Duration::from_millis(8000)));

        // Fifth delay should be 16000ms
        assert_eq!(strategy.next_delay(), Some(Duration::from_millis(16000)));

        // Sixth should be None (max attempts reached)
        assert_eq!(strategy.next_delay(), None);

        // Reset and verify
        strategy.reset();
        assert_eq!(strategy.attempts(), 0);
        assert_eq!(strategy.next_delay(), Some(Duration::from_millis(1000)));
    }

    #[test]
    fn test_reconnect_strategy_unlimited() {
        let config = WebSocketConfig {
            reconnect_initial_delay_ms: 1000,
            reconnect_max_delay_ms: 4000,
            reconnect_multiplier: 2.0,
            max_reconnect_attempts: 0, // unlimited
            heartbeat_interval_secs: 30,
            heartbeat_timeout_secs: 10,
            enable_heartbeat: true,
        };

        let mut strategy = ReconnectStrategy::new(&config);

        // Should not hit max
        for _ in 0..10 {
            assert!(strategy.next_delay().is_some());
        }

        // Should cap at max delay
        let delay = strategy.next_delay().unwrap();
        assert_eq!(delay, Duration::from_millis(4000));
    }
}
