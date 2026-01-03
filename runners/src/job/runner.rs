//! Main job runner implementation

use anyhow::Result;
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Mutex;
use tracing::{info, warn, error, debug};

use crate::config::Settings;
use crate::client::{ControlPlaneClient, WebSocketClient};
use crate::client::websocket::{IncomingMessage, JobSpec, StepSpec};
use crate::executor::{Executor, ExecutorType, ExecutionContext, create_executor};

/// Main job runner
pub struct JobRunner {
    settings: Settings,
    client: ControlPlaneClient,
    current_jobs: Arc<Mutex<u32>>,
}

impl JobRunner {
    pub fn new(settings: Settings, client: ControlPlaneClient) -> Self {
        Self {
            settings,
            client,
            current_jobs: Arc::new(Mutex::new(0)),
        }
    }

    /// Main run loop
    pub async fn run(self) -> Result<()> {
        let mut reconnect_delay = Duration::from_secs(1);
        let max_delay = Duration::from_secs(60);

        loop {
            info!("Connecting to control plane...");

            match self.run_connection().await {
                Ok(_) => {
                    info!("Connection closed normally");
                    reconnect_delay = Duration::from_secs(1);
                }
                Err(e) => {
                    error!("Connection error: {}", e);
                }
            }

            // Wait before reconnecting
            info!("Reconnecting in {:?}...", reconnect_delay);
            tokio::time::sleep(reconnect_delay).await;

            // Exponential backoff
            reconnect_delay = std::cmp::min(reconnect_delay * 2, max_delay);
        }
    }

    async fn run_connection(&self) -> Result<()> {
        let mut ws = self.client.connect_websocket().await?;
        info!("Connected to control plane");

        // Start heartbeat task
        let heartbeat_handle = self.spawn_heartbeat_task();

        loop {
            tokio::select! {
                // Receive messages from control plane
                message = ws.receive() => {
                    match message {
                        Ok(Some(msg)) => {
                            if let Err(e) = self.handle_message(&mut ws, msg).await {
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
        Ok(())
    }

    fn spawn_heartbeat_task(&self) -> tokio::task::JoinHandle<()> {
        let settings = self.settings.clone();
        let client = ControlPlaneClient::new(settings.clone());
        let current_jobs = self.current_jobs.clone();

        tokio::spawn(async move {
            let interval = Duration::from_secs(settings.runner.heartbeat_interval_secs);

            loop {
                tokio::time::sleep(interval).await;

                match client.connect_websocket().await {
                    Ok(mut ws) => {
                        let jobs = *current_jobs.lock().await;
                        if let Err(e) = ws.send_heartbeat(&settings.runner.id, jobs).await {
                            warn!("Failed to send heartbeat: {}", e);
                        }
                    }
                    Err(e) => {
                        warn!("Failed to connect for heartbeat: {}", e);
                    }
                }
            }
        })
    }

    async fn handle_message(
        &self,
        ws: &mut WebSocketClient,
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
                    return Ok(());
                }

                // Increment job count
                *self.current_jobs.lock().await += 1;

                // Spawn job execution task
                let ws_settings = self.settings.clone();
                let current_jobs = self.current_jobs.clone();

                tokio::spawn(async move {
                    if let Err(e) = execute_job(ws_settings, job).await {
                        error!("Job execution failed: {}", e);
                    }

                    // Decrement job count
                    *current_jobs.lock().await -= 1;
                });
            }

            IncomingMessage::JobCancel { job_id } => {
                warn!("Received cancel request for job: {}", job_id);
                // TODO: Implement job cancellation
            }

            IncomingMessage::Error { message } => {
                error!("Received error from control plane: {}", message);
            }
        }

        Ok(())
    }
}

/// Execute a job
async fn execute_job(settings: Settings, job: JobSpec) -> Result<()> {
    info!("Executing job: {} ({})", job.name, job.job_id);

    // Connect to control plane for status updates
    let client = ControlPlaneClient::new(settings.clone());
    let mut ws = client.connect_websocket().await?;

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

    // Execute steps
    let mut job_outputs = HashMap::new();
    let mut job_status = "success";

    for step in &job.steps {
        match execute_step(&mut ws, &executor, &job, step, &workspace_path).await {
            Ok(outputs) => {
                job_outputs.extend(outputs);
            }
            Err(e) => {
                error!("Step {} failed: {}", step.name, e);
                if !step.continue_on_error {
                    job_status = "failed";
                    break;
                }
            }
        }
    }

    // Update job status
    ws.send_status_update(
        "job",
        &job.job_id,
        job_status,
        None,
        job_outputs.clone(),
    ).await?;

    info!("Job {} completed with status: {}", job.job_id, job_status);

    // Cleanup workspace
    if let Err(e) = tokio::fs::remove_dir_all(&workspace_path).await {
        warn!("Failed to cleanup workspace: {}", e);
    }

    Ok(())
}

/// Execute a single step
async fn execute_step(
    ws: &mut WebSocketClient,
    executor: &Box<dyn Executor>,
    job: &JobSpec,
    step: &StepSpec,
    workspace_path: &PathBuf,
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
        timeout: Duration::from_secs(step.timeout_minutes as u64 * 60),
        container_image: job.container.as_ref().map(|c| c.image.clone()),
        container_options: None,
    };

    // Prepare and execute
    executor.prepare(&ctx).await?;

    let result = executor.execute(&ctx).await?;

    // Send logs
    if !result.stdout.is_empty() {
        ws.send_log(&job.job_id, &step.step_id, &result.stdout, "info").await?;
    }
    if !result.stderr.is_empty() {
        ws.send_log(&job.job_id, &step.step_id, &result.stderr, "error").await?;
    }

    // Parse outputs (GitHub Actions style)
    let outputs = parse_outputs(&result.stdout);

    // Determine status
    let status = if result.timed_out {
        "timeout"
    } else if result.success() {
        "success"
    } else {
        "failed"
    };

    // Update step status
    ws.send_status_update(
        "step",
        &step.step_id,
        status,
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

        // Parse GITHUB_OUTPUT file format (key=value)
        // This is a simplified version; real implementation would need file handling
    }

    outputs
}
