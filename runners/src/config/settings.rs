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

impl Settings {
    /// Load settings from environment and config file
    pub fn load() -> Result<Self> {
        dotenvy::dotenv().ok();

        let config = config::Config::builder()
            // Default values
            .set_default("runner.max_concurrent_jobs", 2)?
            .set_default("runner.heartbeat_interval_secs", 30)?
            .set_default("control_plane.timeout_secs", 30)?
            .set_default("control_plane.reconnect_delay_secs", 5)?
            .set_default("executor.enabled", vec!["shell"])?
            .set_default("workspace.base_path", "/tmp/muelsyse/workspaces")?
            .set_default("workspace.artifact_path", "/tmp/muelsyse/artifacts")?
            .set_default("workspace.cache_path", "/tmp/muelsyse/cache")?
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
