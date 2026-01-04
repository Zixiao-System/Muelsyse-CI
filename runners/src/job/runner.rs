//! Main job runner implementation
//!
//! Features:
//! - Job execution with timeout handling
//! - Retry logic with configurable attempts
//! - Graceful error reporting
//! - Job cancellation support
//! - Connection state awareness

use anyhow::Result;
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{Mutex, RwLock, broadcast};
use tokio::time::timeout;
use tracing::{info, warn, error, debug};

use crate::config::{Settings, JobConfig};
use crate::client::{ControlPlaneClient, WebSocketClient, ConnectionState, IncomingMessage, JobSpec, StepSpec};
use crate::executor::{Executor, ExecutorType, ExecutionContext, create_executor};
use crate::log::{LogStreamer, LogStreamerManager};

// ============================================================================
// Job Status Types
// ============================================================================

/// Job execution status
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum JobStatus {
    Pending,
    Running,
    Success,
    Failed,
    Timeout,
    Cancelled,
}

impl std::fmt::Display for JobStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Pending => write!(f, "pending"),
            Self::Running => write!(f, "running"),
            Self::Success => write!(f, "success"),
            Self::Failed => write!(f, "failed"),
            Self::Timeout => write!(f, "timeout"),
            Self::Cancelled => write!(f, "cancelled"),
        }
    }
}

/// Step execution status
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StepStatus {
    Pending,
    Running,
    Success,
    Failed,
    Timeout,
    Skipped,
}

impl std::fmt::Display for StepStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Pending => write!(f, "pending"),
            Self::Running => write!(f, "running"),
            Self::Success => write!(f, "success"),
            Self::Failed => write!(f, "failed"),
            Self::Timeout => write!(f, "timeout"),
            Self::Skipped => write!(f, "skipped"),
        }
    }
}

// ============================================================================
// Job Context
// ============================================================================

/// Context for job execution with cancellation support
pub struct JobContext {
    pub job_id: String,
    pub cancel_tx: broadcast::Sender<()>,
    pub cancelled: Arc<RwLock<bool>>,
}

impl JobContext {
    pub fn new(job_id: String) -> Self {
        let (cancel_tx, _) = broadcast::channel(1);
        Self {
            job_id,
            cancel_tx,
            cancelled: Arc::new(RwLock::new(false)),
        }
    }

    pub async fn cancel(&self) {
        *self.cancelled.write().await = true;
        let _ = self.cancel_tx.send(());
    }

    pub async fn is_cancelled(&self) -> bool {
        *self.cancelled.read().await
    }

    pub fn subscribe(&self) -> broadcast::Receiver<()> {
        self.cancel_tx.subscribe()
    }
}

// ============================================================================
// Retry Configuration
// ============================================================================

/// Retry configuration for step execution
#[derive(Debug, Clone)]
pub struct RetryConfig {
    pub max_attempts: u32,
    pub delay_secs: u64,
    pub backoff_multiplier: f64,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_attempts: 3,
            delay_secs: 5,
            backoff_multiplier: 2.0,
        }
    }
}

impl From<&JobConfig> for RetryConfig {
    fn from(config: &JobConfig) -> Self {
        Self {
            max_attempts: config.max_retries,
            delay_secs: config.retry_delay_secs,
            backoff_multiplier: 2.0,
        }
    }
}

// ============================================================================
// Main Job Runner
// ============================================================================

/// Main job runner with enhanced error handling
pub struct JobRunner {
    settings: Settings,
    client: ControlPlaneClient,
    current_jobs: Arc<Mutex<u32>>,
    job_contexts: Arc<RwLock<HashMap<String, Arc<JobContext>>>>,
    log_manager: Arc<LogStreamerManager>,
    shutdown_tx: broadcast::Sender<()>,
}

impl JobRunner {
    pub fn new(settings: Settings, client: ControlPlaneClient) -> Self {
        let log_manager = Arc::new(LogStreamerManager::new(settings.logging.clone()));
        let (shutdown_tx, _) = broadcast::channel(1);

        Self {
            settings,
            client,
            current_jobs: Arc::new(Mutex::new(0)),
            job_contexts: Arc::new(RwLock::new(HashMap::new())),
            log_manager,
            shutdown_tx,
        }
    }

    /// Get shutdown sender for external shutdown signaling
    pub fn shutdown_sender(&self) -> broadcast::Sender<()> {
        self.shutdown_tx.clone()
    }

    /// Main run loop with graceful shutdown support
    pub async fn run(self) -> Result<()> {
        let mut reconnect_delay = Duration::from_millis(
            self.settings.websocket.reconnect_initial_delay_ms
        );
        let max_delay = Duration::from_millis(
            self.settings.websocket.reconnect_max_delay_ms
        );

        // Create a separate receiver for the main loop
        let mut shutdown_rx = self.shutdown_tx.subscribe();

        loop {
            info!("Connecting to control plane...");

            tokio::select! {
                biased;

                _ = shutdown_rx.recv() => {
                    info!("Received shutdown signal, stopping runner...");
                    break;
                }

                result = self.run_connection() => {
                    match result {
                        Ok(_) => {
                            info!("Connection closed normally");
                            reconnect_delay = Duration::from_millis(
                                self.settings.websocket.reconnect_initial_delay_ms
                            );
                        }
                        Err(e) => {
                            error!("Connection error: {}", e);
                        }
                    }
                }
            }

            // Check if shutdown was requested
            if shutdown_rx.try_recv().is_ok() {
                break;
            }

            // Wait before reconnecting
            info!("Reconnecting in {:?}...", reconnect_delay);
            tokio::time::sleep(reconnect_delay).await;

            // Exponential backoff
            reconnect_delay = std::cmp::min(
                Duration::from_millis(
                    (reconnect_delay.as_millis() as f64 *
                     self.settings.websocket.reconnect_multiplier) as u64
                ),
                max_delay,
            );
        }

        // Wait for running jobs to complete
        self.wait_for_jobs_completion().await;

        Ok(())
    }

    /// Wait for all running jobs to complete
    async fn wait_for_jobs_completion(&self) {
        let timeout_secs = self.settings.job.shutdown_timeout_secs;
        let start = Instant::now();

        loop {
            let job_count = *self.current_jobs.lock().await;
            if job_count == 0 {
                info!("All jobs completed");
                break;
            }

            if start.elapsed() > Duration::from_secs(timeout_secs) {
                warn!(
                    "Shutdown timeout reached, {} jobs still running",
                    job_count
                );
                // Cancel remaining jobs
                self.cancel_all_jobs().await;
                break;
            }

            info!("Waiting for {} jobs to complete...", job_count);
            tokio::time::sleep(Duration::from_secs(1)).await;
        }
    }

    /// Cancel all running jobs
    async fn cancel_all_jobs(&self) {
        let contexts = self.job_contexts.read().await;
        for (job_id, ctx) in contexts.iter() {
            info!("Cancelling job: {}", job_id);
            ctx.cancel().await;
        }
    }

    async fn run_connection(&self) -> Result<()> {
        let ws = Arc::new(self.client.connect_websocket().await?);

        // Wait for connection to be established
        ws.wait_connected(Duration::from_secs(30)).await?;
        info!("Connected to control plane");

        // Register connection state callback
        let log_manager = self.log_manager.clone();
        ws.on_state_change(Arc::new(move |state| {
            if state == ConnectionState::Connected {
                // Trigger resend of pending logs on reconnection
                let log_mgr = log_manager.clone();
                tokio::spawn(async move {
                    if let Err(e) = log_mgr.flush_all().await {
                        warn!("Failed to flush logs on reconnect: {}", e);
                    }
                });
            }
        })).await;

        // Start heartbeat task
        let heartbeat_handle = self.spawn_heartbeat_task(ws.clone());

        // Create shutdown receiver for this connection
        let mut shutdown_rx = self.shutdown_tx.subscribe();

        // Message processing loop
        loop {
            tokio::select! {
                biased;

                _ = shutdown_rx.recv() => {
                    info!("Shutdown signal received during connection");
                    break;
                }

                message = ws.receive() => {
                    match message {
                        Ok(Some(msg)) => {
                            if let Err(e) = self.handle_message(ws.clone(), msg).await {
                                error!("Error handling message: {}", e);
                            }
                        }
                        Ok(None) => {
                            // Keep-alive or ignored message
                        }
                        Err(e) => {
                            error!("WebSocket error: {}", e);
                            break;
                        }
                    }
                }
            }
        }

        heartbeat_handle.abort();
        ws.close().await?;
        Ok(())
    }

    fn spawn_heartbeat_task(&self, ws: Arc<WebSocketClient>) -> tokio::task::JoinHandle<()> {
        let settings = self.settings.clone();
        let current_jobs = self.current_jobs.clone();

        tokio::spawn(async move {
            let interval = Duration::from_secs(settings.runner.heartbeat_interval_secs);

            loop {
                tokio::time::sleep(interval).await;

                if ws.is_connected().await {
                    let jobs = *current_jobs.lock().await;
                    if let Err(e) = ws.send_heartbeat(&settings.runner.id, jobs).await {
                        warn!("Failed to send heartbeat: {}", e);
                    }
                }
            }
        })
    }

    async fn handle_message(
        &self,
        ws: Arc<WebSocketClient>,
        message: IncomingMessage,
    ) -> Result<()> {
        match message {
            IncomingMessage::Connected { runner_id } => {
                info!("Confirmed connection as runner: {}", runner_id);
            }

            IncomingMessage::HeartbeatAck { timestamp } => {
                debug!("Heartbeat acknowledged at {}", timestamp);
            }

            IncomingMessage::JobAssignment { job } => {
                info!("Received job assignment: {} ({})", job.name, job.job_id);

                // Check capacity
                let jobs = *self.current_jobs.lock().await;
                if jobs >= self.settings.runner.max_concurrent_jobs as u32 {
                    warn!("At capacity, cannot accept job");
                    // Notify control plane we're at capacity
                    ws.send_status_update(
                        "job",
                        &job.job_id,
                        "rejected",
                        None,
                        HashMap::from([("reason".to_string(), "runner_at_capacity".to_string())]),
                    ).await?;
                    return Ok(());
                }

                // Increment job count
                *self.current_jobs.lock().await += 1;

                // Create job context
                let job_ctx = Arc::new(JobContext::new(job.job_id.clone()));
                self.job_contexts.write().await.insert(job.job_id.clone(), job_ctx.clone());

                // Spawn job execution task
                let settings = self.settings.clone();
                let current_jobs = self.current_jobs.clone();
                let job_contexts = self.job_contexts.clone();
                let log_manager = self.log_manager.clone();
                let job_id = job.job_id.clone();

                tokio::spawn(async move {
                    let result = execute_job_with_retry(
                        settings.clone(),
                        job,
                        job_ctx,
                        log_manager,
                    ).await;

                    if let Err(e) = result {
                        error!("Job execution failed: {}", e);
                    }

                    // Cleanup
                    job_contexts.write().await.remove(&job_id);
                    *current_jobs.lock().await -= 1;
                });
            }

            IncomingMessage::JobCancel { job_id } => {
                warn!("Received cancel request for job: {}", job_id);

                if let Some(ctx) = self.job_contexts.read().await.get(&job_id) {
                    ctx.cancel().await;
                    info!("Job {} cancellation requested", job_id);
                } else {
                    warn!("Job {} not found for cancellation", job_id);
                }
            }

            IncomingMessage::LogAck { job_id, last_sequence } => {
                debug!("Log acknowledged: job={}, seq={}", job_id, last_sequence);
                let streamer = self.log_manager.get_or_create(&job_id).await;
                streamer.acknowledge("", last_sequence).await;
            }

            IncomingMessage::Error { message } => {
                error!("Received error from control plane: {}", message);
            }

            IncomingMessage::Pong { timestamp } => {
                debug!("Received pong: {}", timestamp);
            }
        }

        Ok(())
    }

    /// Get current job count
    pub async fn current_job_count(&self) -> u32 {
        *self.current_jobs.lock().await
    }

    /// Check if runner is at capacity
    pub async fn is_at_capacity(&self) -> bool {
        *self.current_jobs.lock().await >= self.settings.runner.max_concurrent_jobs as u32
    }
}

// ============================================================================
// Job Execution with Retry
// ============================================================================

/// Execute a job with retry logic
async fn execute_job_with_retry(
    settings: Settings,
    job: JobSpec,
    ctx: Arc<JobContext>,
    log_manager: Arc<LogStreamerManager>,
) -> Result<()> {
    let retry_config = RetryConfig::from(&settings.job);
    let mut attempts = 0;
    let mut last_error: Option<anyhow::Error> = None;

    while attempts < retry_config.max_attempts {
        attempts += 1;

        if ctx.is_cancelled().await {
            info!("Job {} was cancelled before attempt {}", job.job_id, attempts);
            return report_job_status(&settings, &job.job_id, JobStatus::Cancelled, None).await;
        }

        info!(
            "Executing job {} (attempt {}/{})",
            job.job_id, attempts, retry_config.max_attempts
        );

        match execute_job(settings.clone(), job.clone(), ctx.clone(), log_manager.clone()).await {
            Ok(_) => return Ok(()),
            Err(e) => {
                last_error = Some(e);

                if attempts < retry_config.max_attempts {
                    let delay = Duration::from_secs(
                        (retry_config.delay_secs as f64 *
                         retry_config.backoff_multiplier.powi(attempts as i32 - 1)) as u64
                    );
                    warn!(
                        "Job {} failed, retrying in {:?}...",
                        job.job_id, delay
                    );
                    tokio::time::sleep(delay).await;
                }
            }
        }
    }

    // All retries exhausted
    error!(
        "Job {} failed after {} attempts",
        job.job_id, retry_config.max_attempts
    );

    if let Some(e) = last_error {
        report_job_status(
            &settings,
            &job.job_id,
            JobStatus::Failed,
            Some(&format!("Failed after {} attempts: {}", attempts, e)),
        ).await?;
    }

    Ok(())
}

/// Report job status to control plane
async fn report_job_status(
    settings: &Settings,
    job_id: &str,
    status: JobStatus,
    error_message: Option<&str>,
) -> Result<()> {
    let client = ControlPlaneClient::new(settings.clone());
    let ws = client.connect_websocket().await?;

    let mut outputs = HashMap::new();
    if let Some(msg) = error_message {
        outputs.insert("error".to_string(), msg.to_string());
    }

    ws.send_status_update(
        "job",
        job_id,
        &status.to_string(),
        None,
        outputs,
    ).await?;

    Ok(())
}

/// Execute a job
async fn execute_job(
    settings: Settings,
    job: JobSpec,
    ctx: Arc<JobContext>,
    log_manager: Arc<LogStreamerManager>,
) -> Result<()> {
    info!("Executing job: {} ({})", job.name, job.job_id);

    // Connect to control plane for status updates
    let client = ControlPlaneClient::new(settings.clone());
    let ws = Arc::new(client.connect_websocket().await?);
    ws.wait_connected(Duration::from_secs(10)).await?;

    // Get log streamer for this job
    let log_streamer = log_manager.get_or_create(&job.job_id).await;

    // Update job status to running
    ws.send_status_update(
        "job",
        &job.job_id,
        "running",
        None,
        HashMap::new(),
    ).await?;

    // Prepare workspace
    let workspace_path = PathBuf::from(&settings.workspace.base_path)
        .join(&job.job_id);

    tokio::fs::create_dir_all(&workspace_path).await?;

    // Determine executor type
    let executor_type = if job.container.is_some() {
        ExecutorType::Docker
    } else {
        ExecutorType::Shell
    };

    let executor = create_executor(executor_type, &settings)?;

    // Calculate job timeout
    let job_timeout = Duration::from_secs(
        job.timeout_minutes.max(settings.job.default_timeout_minutes) as u64 * 60
    );

    // Execute steps with job-level timeout
    let mut cancel_rx = ctx.subscribe();

    let execution_result = tokio::select! {
        result = execute_steps_with_timeout(
            ws.clone(),
            &executor,
            &job,
            &workspace_path,
            &settings,
            ctx.clone(),
            log_streamer.clone(),
            job_timeout,
        ) => result,
        _ = cancel_rx.recv() => {
            warn!("Job {} cancelled during execution", job.job_id);
            Err(anyhow::anyhow!("Job cancelled"))
        }
    };

    // Determine final status
    let (job_status, job_outputs) = match execution_result {
        Ok(outputs) => (JobStatus::Success, outputs),
        Err(e) => {
            if ctx.is_cancelled().await {
                (JobStatus::Cancelled, HashMap::new())
            } else if e.to_string().contains("timeout") {
                (JobStatus::Timeout, HashMap::new())
            } else {
                let mut outputs = HashMap::new();
                outputs.insert("error".to_string(), e.to_string());
                (JobStatus::Failed, outputs)
            }
        }
    };

    // Flush remaining logs
    if let Err(e) = log_streamer.flush().await {
        warn!("Failed to flush final logs: {}", e);
    }

    // Update job status
    ws.send_status_update(
        "job",
        &job.job_id,
        &job_status.to_string(),
        None,
        job_outputs.clone(),
    ).await?;

    info!("Job {} completed with status: {}", job.job_id, job_status);

    // Cleanup workspace
    if let Err(e) = tokio::fs::remove_dir_all(&workspace_path).await {
        warn!("Failed to cleanup workspace: {}", e);
    }

    // Cleanup log streamer
    log_manager.remove(&job.job_id).await;

    if job_status == JobStatus::Success {
        Ok(())
    } else {
        Err(anyhow::anyhow!("Job failed with status: {}", job_status))
    }
}

/// Execute all steps with timeout
async fn execute_steps_with_timeout(
    ws: Arc<WebSocketClient>,
    executor: &Box<dyn Executor>,
    job: &JobSpec,
    workspace_path: &PathBuf,
    settings: &Settings,
    ctx: Arc<JobContext>,
    log_streamer: Arc<LogStreamer>,
    job_timeout: Duration,
) -> Result<HashMap<String, String>> {
    let start = Instant::now();
    let mut job_outputs = HashMap::new();

    for step in &job.steps {
        // Check job timeout
        if start.elapsed() > job_timeout {
            error!("Job timeout exceeded");
            return Err(anyhow::anyhow!("Job timeout exceeded"));
        }

        // Check cancellation
        if ctx.is_cancelled().await {
            return Err(anyhow::anyhow!("Job cancelled"));
        }

        // Calculate remaining time for step
        let remaining = job_timeout.saturating_sub(start.elapsed());
        let step_timeout = Duration::from_secs(
            step.timeout_minutes.max(settings.job.default_step_timeout_minutes) as u64 * 60
        ).min(remaining);

        match execute_step_with_timeout(
            ws.clone(),
            executor,
            job,
            step,
            workspace_path,
            step_timeout,
            log_streamer.clone(),
        ).await {
            Ok(outputs) => {
                job_outputs.extend(outputs);
            }
            Err(e) => {
                error!("Step {} failed: {}", step.name, e);
                if !step.continue_on_error {
                    return Err(e);
                }
            }
        }
    }

    Ok(job_outputs)
}

/// Execute a single step with timeout
async fn execute_step_with_timeout(
    ws: Arc<WebSocketClient>,
    executor: &Box<dyn Executor>,
    job: &JobSpec,
    step: &StepSpec,
    workspace_path: &PathBuf,
    step_timeout: Duration,
    log_streamer: Arc<LogStreamer>,
) -> Result<HashMap<String, String>> {
    info!("Executing step: {} ({})", step.name, step.step_id);

    // Update step status to running
    ws.send_status_update(
        "step",
        &step.step_id,
        "running",
        None,
        HashMap::new(),
    ).await?;

    // Build environment
    let mut env = job.environment.clone();
    env.extend(step.env.clone());

    // Add secrets (masked in logs)
    for (key, value) in &job.secrets {
        env.insert(key.clone(), value.clone());
    }

    // Build execution context
    let working_dir = if let Some(ref wd) = step.working_directory {
        workspace_path.join(wd)
    } else {
        workspace_path.clone()
    };

    let command = step.run.clone().unwrap_or_default();

    let ctx = ExecutionContext {
        job_id: job.job_id.clone(),
        step_id: step.step_id.clone(),
        command,
        shell: step.shell.clone(),
        working_directory: working_dir,
        environment: env,
        timeout: step_timeout,
        container_image: job.container.as_ref().map(|c| c.image.clone()),
        container_options: None,
    };

    // Prepare and execute with timeout
    executor.prepare(&ctx).await?;

    let result = match timeout(step_timeout, executor.execute(&ctx)).await {
        Ok(Ok(result)) => result,
        Ok(Err(e)) => {
            // Execution error
            ws.send_status_update(
                "step",
                &step.step_id,
                "failed",
                None,
                HashMap::from([("error".to_string(), e.to_string())]),
            ).await?;
            return Err(e);
        }
        Err(_) => {
            // Timeout
            ws.send_status_update(
                "step",
                &step.step_id,
                "timeout",
                None,
                HashMap::new(),
            ).await?;
            return Err(anyhow::anyhow!("Step timeout after {:?}", step_timeout));
        }
    };

    // Send logs using streamer
    if !result.stdout.is_empty() {
        log_streamer.add(&step.step_id, &result.stdout, "info").await?;
    }
    if !result.stderr.is_empty() {
        log_streamer.add(&step.step_id, &result.stderr, "error").await?;
    }

    // Flush logs for this step
    log_streamer.flush().await?;

    // Parse outputs (GitHub Actions style)
    let outputs = parse_outputs(&result.stdout);

    // Determine status
    let status = if result.timed_out {
        StepStatus::Timeout
    } else if result.success() {
        StepStatus::Success
    } else {
        StepStatus::Failed
    };

    // Update step status
    ws.send_status_update(
        "step",
        &step.step_id,
        &status.to_string(),
        Some(result.exit_code),
        outputs.clone(),
    ).await?;

    // Cleanup
    executor.cleanup(&ctx).await?;

    if !result.success() && !step.continue_on_error {
        anyhow::bail!("Step failed with exit code {}", result.exit_code);
    }

    Ok(outputs)
}

/// Parse GitHub Actions style outputs from stdout
fn parse_outputs(stdout: &str) -> HashMap<String, String> {
    let mut outputs = HashMap::new();

    for line in stdout.lines() {
        // Parse ::set-output name=key::value format
        if line.starts_with("::set-output name=") {
            if let Some(rest) = line.strip_prefix("::set-output name=") {
                if let Some((name, value)) = rest.split_once("::") {
                    outputs.insert(name.to_string(), value.to_string());
                }
            }
        }

        // Parse GITHUB_OUTPUT style: key=value (for multi-line, use delimiter)
        if line.contains('=') && !line.starts_with("::") {
            if let Some((key, value)) = line.split_once('=') {
                let key = key.trim();
                let value = value.trim();
                if !key.is_empty() && !key.contains(' ') {
                    outputs.insert(key.to_string(), value.to_string());
                }
            }
        }
    }

    outputs
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_outputs() {
        let stdout = r#"
Hello World
::set-output name=result::success
::set-output name=count::42
BUILD_ID=123
"#;

        let outputs = parse_outputs(stdout);
        assert_eq!(outputs.get("result"), Some(&"success".to_string()));
        assert_eq!(outputs.get("count"), Some(&"42".to_string()));
        assert_eq!(outputs.get("BUILD_ID"), Some(&"123".to_string()));
    }

    #[test]
    fn test_job_status_display() {
        assert_eq!(JobStatus::Running.to_string(), "running");
        assert_eq!(JobStatus::Success.to_string(), "success");
        assert_eq!(JobStatus::Failed.to_string(), "failed");
        assert_eq!(JobStatus::Timeout.to_string(), "timeout");
        assert_eq!(JobStatus::Cancelled.to_string(), "cancelled");
    }

    #[test]
    fn test_retry_config_from_job_config() {
        let job_config = JobConfig {
            default_timeout_minutes: 60,
            default_step_timeout_minutes: 10,
            max_retries: 5,
            retry_delay_secs: 10,
            shutdown_timeout_secs: 300,
        };

        let retry_config = RetryConfig::from(&job_config);
        assert_eq!(retry_config.max_attempts, 5);
        assert_eq!(retry_config.delay_secs, 10);
    }

    #[tokio::test]
    async fn test_job_context_cancellation() {
        let ctx = JobContext::new("test-job".to_string());

        assert!(!ctx.is_cancelled().await);

        ctx.cancel().await;

        assert!(ctx.is_cancelled().await);
    }
}
