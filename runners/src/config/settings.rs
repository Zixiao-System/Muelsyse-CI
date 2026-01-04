//! Runner settings and configuration

use anyhow::{Result, Context};
use serde::Deserialize;
use std::path::PathBuf;

/// Main configuration structure
#[derive(Debug, Clone, Deserialize)]
pub struct Settings {
    pub runner: RunnerConfig,
    pub control_plane: ControlPlaneConfig,
    pub executor: ExecutorConfig,
    pub workspace: WorkspaceConfig,
    #[serde(default)]
    pub websocket: WebSocketConfig,
    #[serde(default)]
    pub logging: LoggingConfig,
    #[serde(default)]
    pub job: JobConfig,
}

/// Runner identification and capabilities
#[derive(Debug, Clone, Deserialize)]
pub struct RunnerConfig {
    /// Unique runner ID (UUID)
    pub id: String,

    /// Human-readable runner name
    pub name: String,

    /// Authentication token
    pub token: String,

    /// Labels for job matching
    #[serde(default)]
    pub labels: Vec<String>,

    /// Maximum concurrent jobs
    #[serde(default = "default_max_concurrent_jobs")]
    pub max_concurrent_jobs: usize,

    /// Heartbeat interval in seconds
    #[serde(default = "default_heartbeat_interval")]
    pub heartbeat_interval_secs: u64,
}

/// Control plane connection settings
#[derive(Debug, Clone, Deserialize)]
pub struct ControlPlaneConfig {
    /// HTTP API URL (e.g., "http://localhost:8000")
    pub api_url: String,

    /// WebSocket URL (e.g., "ws://localhost:8001")
    pub ws_url: String,

    /// Connection timeout in seconds
    #[serde(default = "default_timeout")]
    pub timeout_secs: u64,

    /// Reconnection delay in seconds
    #[serde(default = "default_reconnect_delay")]
    pub reconnect_delay_secs: u64,
}

/// Executor configuration
#[derive(Debug, Clone, Deserialize)]
pub struct ExecutorConfig {
    /// Available executor types
    #[serde(default = "default_executors")]
    pub enabled: Vec<String>,

    /// Docker-specific settings
    #[serde(default)]
    pub docker: DockerConfig,

    /// Shell-specific settings
    #[serde(default)]
    pub shell: ShellConfig,
}

/// Docker executor configuration
#[derive(Debug, Clone, Deserialize, Default)]
pub struct DockerConfig {
    /// Docker socket path
    #[serde(default = "default_docker_socket")]
    pub socket: String,

    /// Default network mode
    #[serde(default = "default_network_mode")]
    pub network_mode: String,

    /// Memory limit in bytes (0 = unlimited)
    #[serde(default)]
    pub memory_limit: u64,

    /// CPU limit (0 = unlimited)
    #[serde(default)]
    pub cpu_limit: f64,

    /// Pull policy: always, if-not-present, never
    #[serde(default = "default_pull_policy")]
    pub pull_policy: String,
}

/// Shell executor configuration
#[derive(Debug, Clone, Deserialize, Default)]
pub struct ShellConfig {
    /// Default shell to use
    #[serde(default = "default_shell")]
    pub default_shell: String,

    /// Whether to clean up workspace after job
    #[serde(default)]
    pub cleanup_workspace: bool,
}

/// Workspace configuration
#[derive(Debug, Clone, Deserialize)]
pub struct WorkspaceConfig {
    /// Base path for job workspaces
    #[serde(default = "default_workspace_path")]
    pub base_path: PathBuf,

    /// Artifact storage path
    #[serde(default = "default_artifact_path")]
    pub artifact_path: PathBuf,

    /// Cache path
    #[serde(default = "default_cache_path")]
    pub cache_path: PathBuf,
}

/// WebSocket connection configuration
#[derive(Debug, Clone, Deserialize)]
pub struct WebSocketConfig {
    /// Initial reconnect delay in milliseconds
    #[serde(default = "default_reconnect_initial_delay_ms")]
    pub reconnect_initial_delay_ms: u64,

    /// Maximum reconnect delay in milliseconds
    #[serde(default = "default_reconnect_max_delay_ms")]
    pub reconnect_max_delay_ms: u64,

    /// Reconnect backoff multiplier
    #[serde(default = "default_reconnect_multiplier")]
    pub reconnect_multiplier: f64,

    /// Maximum reconnect attempts (0 = unlimited)
    #[serde(default)]
    pub max_reconnect_attempts: u32,

    /// Heartbeat interval in seconds
    #[serde(default = "default_heartbeat_interval_secs")]
    pub heartbeat_interval_secs: u64,

    /// Heartbeat timeout in seconds (no pong response)
    #[serde(default = "default_heartbeat_timeout_secs")]
    pub heartbeat_timeout_secs: u64,

    /// Enable ping/pong heartbeat
    #[serde(default = "default_enable_heartbeat")]
    pub enable_heartbeat: bool,
}

impl Default for WebSocketConfig {
    fn default() -> Self {
        Self {
            reconnect_initial_delay_ms: default_reconnect_initial_delay_ms(),
            reconnect_max_delay_ms: default_reconnect_max_delay_ms(),
            reconnect_multiplier: default_reconnect_multiplier(),
            max_reconnect_attempts: 0,
            heartbeat_interval_secs: default_heartbeat_interval_secs(),
            heartbeat_timeout_secs: default_heartbeat_timeout_secs(),
            enable_heartbeat: default_enable_heartbeat(),
        }
    }
}

/// Logging configuration
#[derive(Debug, Clone, Deserialize)]
pub struct LoggingConfig {
    /// Log buffer size (number of entries before flush)
    #[serde(default = "default_log_buffer_size")]
    pub buffer_size: usize,

    /// Maximum log chunk size in bytes
    #[serde(default = "default_log_chunk_size")]
    pub chunk_size_bytes: usize,

    /// Flush interval in milliseconds
    #[serde(default = "default_log_flush_interval_ms")]
    pub flush_interval_ms: u64,

    /// Enable log persistence for retry on disconnect
    #[serde(default = "default_enable_log_persistence")]
    pub enable_persistence: bool,

    /// Maximum pending logs before dropping oldest
    #[serde(default = "default_max_pending_logs")]
    pub max_pending_logs: usize,
}

impl Default for LoggingConfig {
    fn default() -> Self {
        Self {
            buffer_size: default_log_buffer_size(),
            chunk_size_bytes: default_log_chunk_size(),
            flush_interval_ms: default_log_flush_interval_ms(),
            enable_persistence: default_enable_log_persistence(),
            max_pending_logs: default_max_pending_logs(),
        }
    }
}

/// Job execution configuration
#[derive(Debug, Clone, Deserialize)]
pub struct JobConfig {
    /// Default job timeout in minutes
    #[serde(default = "default_job_timeout_minutes")]
    pub default_timeout_minutes: u32,

    /// Default step timeout in minutes
    #[serde(default = "default_step_timeout_minutes")]
    pub default_step_timeout_minutes: u32,

    /// Maximum retry attempts for failed jobs
    #[serde(default = "default_max_retries")]
    pub max_retries: u32,

    /// Retry delay in seconds
    #[serde(default = "default_retry_delay_secs")]
    pub retry_delay_secs: u64,

    /// Graceful shutdown timeout in seconds
    #[serde(default = "default_shutdown_timeout_secs")]
    pub shutdown_timeout_secs: u64,
}

impl Default for JobConfig {
    fn default() -> Self {
        Self {
            default_timeout_minutes: default_job_timeout_minutes(),
            default_step_timeout_minutes: default_step_timeout_minutes(),
            max_retries: default_max_retries(),
            retry_delay_secs: default_retry_delay_secs(),
            shutdown_timeout_secs: default_shutdown_timeout_secs(),
        }
    }
}

// Default value functions
fn default_max_concurrent_jobs() -> usize { 2 }
fn default_heartbeat_interval() -> u64 { 30 }
fn default_timeout() -> u64 { 30 }
fn default_reconnect_delay() -> u64 { 5 }
fn default_executors() -> Vec<String> { vec!["shell".into()] }
fn default_docker_socket() -> String { "/var/run/docker.sock".into() }
fn default_network_mode() -> String { "bridge".into() }
fn default_pull_policy() -> String { "if-not-present".into() }
fn default_shell() -> String { "bash".into() }
fn default_workspace_path() -> PathBuf { PathBuf::from("/tmp/muelsyse/workspaces") }
fn default_artifact_path() -> PathBuf { PathBuf::from("/tmp/muelsyse/artifacts") }
fn default_cache_path() -> PathBuf { PathBuf::from("/tmp/muelsyse/cache") }

// WebSocket defaults
fn default_reconnect_initial_delay_ms() -> u64 { 1000 }     // 1 second
fn default_reconnect_max_delay_ms() -> u64 { 60000 }        // 60 seconds
fn default_reconnect_multiplier() -> f64 { 2.0 }
fn default_heartbeat_interval_secs() -> u64 { 30 }
fn default_heartbeat_timeout_secs() -> u64 { 10 }
fn default_enable_heartbeat() -> bool { true }

// Logging defaults
fn default_log_buffer_size() -> usize { 100 }
fn default_log_chunk_size() -> usize { 65536 }              // 64KB
fn default_log_flush_interval_ms() -> u64 { 1000 }          // 1 second
fn default_enable_log_persistence() -> bool { true }
fn default_max_pending_logs() -> usize { 10000 }

// Job defaults
fn default_job_timeout_minutes() -> u32 { 360 }             // 6 hours
fn default_step_timeout_minutes() -> u32 { 60 }             // 1 hour
fn default_max_retries() -> u32 { 3 }
fn default_retry_delay_secs() -> u64 { 5 }
fn default_shutdown_timeout_secs() -> u64 { 300 }           // 5 minutes

impl Settings {
    /// Load settings from environment and config file
    pub fn load() -> Result<Self> {
        dotenvy::dotenv().ok();

        let config = config::Config::builder()
            // Default values - Runner
            .set_default("runner.max_concurrent_jobs", 2)?
            .set_default("runner.heartbeat_interval_secs", 30)?
            // Default values - Control plane
            .set_default("control_plane.timeout_secs", 30)?
            .set_default("control_plane.reconnect_delay_secs", 5)?
            // Default values - Executor
            .set_default("executor.enabled", vec!["shell"])?
            // Default values - Workspace
            .set_default("workspace.base_path", "/tmp/muelsyse/workspaces")?
            .set_default("workspace.artifact_path", "/tmp/muelsyse/artifacts")?
            .set_default("workspace.cache_path", "/tmp/muelsyse/cache")?
            // Default values - WebSocket
            .set_default("websocket.reconnect_initial_delay_ms", 1000)?
            .set_default("websocket.reconnect_max_delay_ms", 60000)?
            .set_default("websocket.reconnect_multiplier", 2.0)?
            .set_default("websocket.max_reconnect_attempts", 0)?
            .set_default("websocket.heartbeat_interval_secs", 30)?
            .set_default("websocket.heartbeat_timeout_secs", 10)?
            .set_default("websocket.enable_heartbeat", true)?
            // Default values - Logging
            .set_default("logging.buffer_size", 100)?
            .set_default("logging.chunk_size_bytes", 65536)?
            .set_default("logging.flush_interval_ms", 1000)?
            .set_default("logging.enable_persistence", true)?
            .set_default("logging.max_pending_logs", 10000)?
            // Default values - Job
            .set_default("job.default_timeout_minutes", 360)?
            .set_default("job.default_step_timeout_minutes", 60)?
            .set_default("job.max_retries", 3)?
            .set_default("job.retry_delay_secs", 5)?
            .set_default("job.shutdown_timeout_secs", 300)?
            // Config file
            .add_source(config::File::with_name("runner").required(false))
            // Environment variables with MUELSYSE_ prefix
            .add_source(
                config::Environment::with_prefix("MUELSYSE")
                    .separator("__")
                    .try_parsing(true)
            )
            .build()
            .context("Failed to build configuration")?;

        config.try_deserialize().context("Failed to deserialize configuration")
    }
}
