//! Executor trait and common types

use async_trait::async_trait;
use anyhow::Result;
use std::collections::HashMap;
use std::path::PathBuf;
use std::time::Duration;

/// Type of executor
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ExecutorType {
    Shell,
    Docker,
}

impl ExecutorType {
    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "shell" => Some(Self::Shell),
            "docker" => Some(Self::Docker),
            _ => None,
        }
    }
}

/// Context for command execution
#[derive(Debug, Clone)]
pub struct ExecutionContext {
    /// Job ID
    pub job_id: String,

    /// Step ID
    pub step_id: String,

    /// Command to execute
    pub command: String,

    /// Shell type (bash, sh, etc.)
    pub shell: String,

    /// Working directory
    pub working_directory: PathBuf,

    /// Environment variables
    pub environment: HashMap<String, String>,

    /// Execution timeout
    pub timeout: Duration,

    /// Container image (for Docker executor)
    pub container_image: Option<String>,

    /// Container options
    pub container_options: Option<ContainerOptions>,
}

/// Container execution options
#[derive(Debug, Clone, Default)]
pub struct ContainerOptions {
    pub env: HashMap<String, String>,
    pub volumes: Vec<String>,
    pub network_mode: Option<String>,
    pub memory_limit: Option<u64>,
    pub cpu_limit: Option<f64>,
}

/// Result of command execution
#[derive(Debug)]
pub struct ExecutionResult {
    /// Exit code
    pub exit_code: i32,

    /// Standard output
    pub stdout: String,

    /// Standard error
    pub stderr: String,

    /// Execution duration
    pub duration: Duration,

    /// Whether the command was killed due to timeout
    pub timed_out: bool,
}

impl ExecutionResult {
    pub fn success(&self) -> bool {
        self.exit_code == 0 && !self.timed_out
    }
}

/// Trait for job executors
#[async_trait]
pub trait Executor: Send + Sync {
    /// Execute a command
    async fn execute(&self, ctx: &ExecutionContext) -> Result<ExecutionResult>;

    /// Prepare execution environment
    async fn prepare(&self, ctx: &ExecutionContext) -> Result<()>;

    /// Cleanup after execution
    async fn cleanup(&self, ctx: &ExecutionContext) -> Result<()>;

    /// Check if executor is healthy
    async fn health_check(&self) -> Result<bool>;

    /// Get executor type
    fn executor_type(&self) -> ExecutorType;
}
