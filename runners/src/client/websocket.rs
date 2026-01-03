//! WebSocket client for control plane communication

use anyhow::{Result, Context};
use futures_util::{SinkExt, StreamExt};
use tokio_tungstenite::{connect_async, tungstenite::Message as WsMessage};
use serde::{Serialize, Deserialize};
use sha2::{Sha256, Digest};
use tracing::{info, warn, debug};
use uuid::Uuid;
use chrono::{DateTime, Utc};
use std::collections::HashMap;

use crate::config::Settings;

/// WebSocket client for real-time communication
pub struct WebSocketClient {
    sender: futures_util::stream::SplitSink<
        tokio_tungstenite::WebSocketStream<
            tokio_tungstenite::MaybeTlsStream<tokio::net::TcpStream>
        >,
        WsMessage
    >,
    receiver: futures_util::stream::SplitStream<
        tokio_tungstenite::WebSocketStream<
            tokio_tungstenite::MaybeTlsStream<tokio::net::TcpStream>
        >
    >,
}

/// Messages sent from runner to control plane
#[derive(Debug, Serialize)]
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
}

/// Messages received from control plane
#[derive(Debug, Deserialize)]
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

    #[serde(rename = "error")]
    Error { message: String },
}

/// System information for heartbeat
#[derive(Debug, Serialize)]
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

impl WebSocketClient {
    /// Connect to control plane WebSocket
    pub async fn connect(settings: Settings) -> Result<Self> {
        let url = format!(
            "{}/ws/runner/{}/?token={}",
            settings.control_plane.ws_url,
            settings.runner.id,
            settings.runner.token
        );

        info!("Connecting to control plane: {}", settings.control_plane.ws_url);

        let (ws_stream, _) = connect_async(&url)
            .await
            .context("Failed to connect to control plane WebSocket")?;

        let (sender, receiver) = ws_stream.split();

        info!("WebSocket connected successfully");

        Ok(Self { sender, receiver })
    }

    /// Send a message to control plane
    pub async fn send(&mut self, message: &OutgoingMessage) -> Result<()> {
        let json = serde_json::to_string(message)?;
        debug!("Sending: {}", json);
        self.sender.send(WsMessage::Text(json)).await?;
        Ok(())
    }

    /// Receive a message from control plane
    pub async fn receive(&mut self) -> Result<Option<IncomingMessage>> {
        match self.receiver.next().await {
            Some(Ok(WsMessage::Text(text))) => {
                debug!("Received: {}", text);
                let message: IncomingMessage = serde_json::from_str(&text)
                    .context("Failed to parse incoming message")?;
                Ok(Some(message))
            }
            Some(Ok(WsMessage::Ping(data))) => {
                self.sender.send(WsMessage::Pong(data)).await?;
                Ok(None)
            }
            Some(Ok(WsMessage::Close(_))) => {
                warn!("WebSocket closed by server");
                Ok(None)
            }
            Some(Ok(_)) => Ok(None),
            Some(Err(e)) => {
                warn!("WebSocket error: {}", e);
                Err(e.into())
            }
            None => Ok(None),
        }
    }

    /// Send heartbeat
    pub async fn send_heartbeat(
        &mut self,
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
        &mut self,
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
        }).await
    }

    /// Send status update
    pub async fn send_status_update(
        &mut self,
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

    /// Close connection
    pub async fn close(&mut self) -> Result<()> {
        self.sender.close().await?;
        Ok(())
    }
}

/// Get current system information
fn get_system_info() -> SystemInfo {
    use sysinfo::System;

    let mut sys = System::new_all();
    sys.refresh_all();

    let cpu_usage = sys.global_cpu_usage();
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
