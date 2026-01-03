//! Shell executor - runs commands directly on the host

use async_trait::async_trait;
use anyhow::{Result, Context};
use tokio::process::Command;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::time::timeout;
use std::process::Stdio;
use std::time::Instant;
use tracing::{debug, warn};

use super::traits::{Executor, ExecutorType, ExecutionContext, ExecutionResult};
use crate::config::ShellConfig;

/// Shell executor that runs commands directly on the host
pub struct ShellExecutor {
    config: ShellConfig,
}

impl ShellExecutor {
    pub fn new(config: ShellConfig) -> Self {
        Self { config }
    }

    fn get_shell_command(&self, shell: &str) -> (&str, &str) {
        match shell {
            "bash" => ("bash", "-c"),
            "sh" => ("sh", "-c"),
            "zsh" => ("zsh", "-c"),
            "fish" => ("fish", "-c"),
            "pwsh" | "powershell" => ("pwsh", "-Command"),
            "cmd" => ("cmd", "/C"),
            _ => ("bash", "-c"),
        }
    }
}

#[async_trait]
impl Executor for ShellExecutor {
    async fn execute(&self, ctx: &ExecutionContext) -> Result<ExecutionResult> {
        let (shell, flag) = self.get_shell_command(&ctx.shell);
        let start = Instant::now();

        debug!("Executing command in shell '{}': {}", shell, ctx.command);

        let mut cmd = Command::new(shell);
        cmd.arg(flag)
           .arg(&ctx.command)
           .current_dir(&ctx.working_directory)
           .envs(&ctx.environment)
           .stdout(Stdio::piped())
           .stderr(Stdio::piped());

        // Spawn the process
        let mut child = cmd.spawn()
            .context("Failed to spawn shell process")?;

        // Read output with timeout
        let result = timeout(ctx.timeout, async {
            let stdout = child.stdout.take().expect("stdout not captured");
            let stderr = child.stderr.take().expect("stderr not captured");

            let mut stdout_reader = BufReader::new(stdout).lines();
            let mut stderr_reader = BufReader::new(stderr).lines();

            let mut stdout_lines = Vec::new();
            let mut stderr_lines = Vec::new();

            // Read stdout and stderr concurrently
            loop {
                tokio::select! {
                    line = stdout_reader.next_line() => {
                        match line {
                            Ok(Some(l)) => stdout_lines.push(l),
                            Ok(None) => break,
                            Err(e) => {
                                warn!("Error reading stdout: {}", e);
                                break;
                            }
                        }
                    }
                    line = stderr_reader.next_line() => {
                        match line {
                            Ok(Some(l)) => stderr_lines.push(l),
                            Ok(None) => {}
                            Err(e) => {
                                warn!("Error reading stderr: {}", e);
                            }
                        }
                    }
                }
            }

            let status = child.wait().await?;

            Ok::<_, anyhow::Error>((
                status.code().unwrap_or(-1),
                stdout_lines.join("\n"),
                stderr_lines.join("\n"),
            ))
        }).await;

        match result {
            Ok(Ok((exit_code, stdout, stderr))) => {
                Ok(ExecutionResult {
                    exit_code,
                    stdout,
                    stderr,
                    duration: start.elapsed(),
                    timed_out: false,
                })
            }
            Ok(Err(e)) => Err(e),
            Err(_) => {
                // Timeout - kill the process
                warn!("Command timed out, killing process");
                let _ = child.kill().await;

                Ok(ExecutionResult {
                    exit_code: -1,
                    stdout: String::new(),
                    stderr: "Command timed out".to_string(),
                    duration: start.elapsed(),
                    timed_out: true,
                })
            }
        }
    }

    async fn prepare(&self, ctx: &ExecutionContext) -> Result<()> {
        // Create working directory if it doesn't exist
        tokio::fs::create_dir_all(&ctx.working_directory)
            .await
            .context("Failed to create working directory")?;

        debug!("Prepared workspace: {:?}", ctx.working_directory);
        Ok(())
    }

    async fn cleanup(&self, ctx: &ExecutionContext) -> Result<()> {
        if self.config.cleanup_workspace {
            if let Err(e) = tokio::fs::remove_dir_all(&ctx.working_directory).await {
                warn!("Failed to cleanup workspace: {}", e);
            }
        }
        Ok(())
    }

    async fn health_check(&self) -> Result<bool> {
        // Shell executor is always healthy if we can run a simple command
        let output = Command::new("echo")
            .arg("health_check")
            .output()
            .await?;

        Ok(output.status.success())
    }

    fn executor_type(&self) -> ExecutorType {
        ExecutorType::Shell
    }
}
