//! Docker executor - runs commands in Docker containers

use async_trait::async_trait;
use anyhow::{Result, Context};
use bollard::Docker;
use bollard::container::{
    Config, CreateContainerOptions, StartContainerOptions, WaitContainerOptions,
    LogsOptions, RemoveContainerOptions,
};
use bollard::image::CreateImageOptions;
use bollard::exec::{CreateExecOptions, StartExecResults};
use futures_util::StreamExt;
use std::time::Instant;
use std::collections::HashMap;
use tracing::{info, debug, warn};

use super::traits::{Executor, ExecutorType, ExecutionContext, ExecutionResult};
use crate::config::DockerConfig;

/// Docker executor that runs commands in containers
pub struct DockerExecutor {
    docker: Docker,
    config: DockerConfig,
}

impl DockerExecutor {
    pub fn new(config: DockerConfig) -> Result<Self> {
        let docker = if config.socket.starts_with("unix://") || config.socket.starts_with('/') {
            Docker::connect_with_socket(&config.socket, 120, bollard::API_DEFAULT_VERSION)?
        } else {
            Docker::connect_with_socket_defaults()?
        };

        Ok(Self { docker, config })
    }

    async fn pull_image(&self, image: &str) -> Result<()> {
        match self.config.pull_policy.as_str() {
            "never" => {
                debug!("Pull policy is 'never', skipping image pull");
                return Ok(());
            }
            "if-not-present" => {
                // Check if image exists
                if self.docker.inspect_image(image).await.is_ok() {
                    debug!("Image {} already exists, skipping pull", image);
                    return Ok(());
                }
            }
            _ => {} // "always" - always pull
        }

        info!("Pulling image: {}", image);

        let mut stream = self.docker.create_image(
            Some(CreateImageOptions {
                from_image: image,
                ..Default::default()
            }),
            None,
            None,
        );

        while let Some(result) = stream.next().await {
            match result {
                Ok(info) => {
                    if let Some(status) = info.status {
                        debug!("Pull status: {}", status);
                    }
                }
                Err(e) => {
                    warn!("Pull warning: {}", e);
                }
            }
        }

        info!("Successfully pulled image: {}", image);
        Ok(())
    }

    fn build_container_config(&self, ctx: &ExecutionContext) -> Config<String> {
        let mut env: Vec<String> = ctx.environment
            .iter()
            .map(|(k, v)| format!("{}={}", k, v))
            .collect();

        // Add container-specific env if provided
        if let Some(ref opts) = ctx.container_options {
            for (k, v) in &opts.env {
                env.push(format!("{}={}", k, v));
            }
        }

        let image = ctx.container_image.clone().unwrap_or_else(|| "alpine:latest".to_string());

        let mut host_config = bollard::service::HostConfig {
            network_mode: Some(self.config.network_mode.clone()),
            ..Default::default()
        };

        // Add volume mounts
        let mut binds = vec![
            format!("{}:/workspace", ctx.working_directory.display()),
        ];

        if let Some(ref opts) = ctx.container_options {
            binds.extend(opts.volumes.clone());

            if let Some(mem) = opts.memory_limit {
                host_config.memory = Some(mem as i64);
            }
            if let Some(cpu) = opts.cpu_limit {
                host_config.cpu_period = Some(100000);
                host_config.cpu_quota = Some((cpu * 100000.0) as i64);
            }
            if let Some(ref network) = opts.network_mode {
                host_config.network_mode = Some(network.clone());
            }
        }

        if self.config.memory_limit > 0 {
            host_config.memory = Some(self.config.memory_limit as i64);
        }
        if self.config.cpu_limit > 0.0 {
            host_config.cpu_period = Some(100000);
            host_config.cpu_quota = Some((self.config.cpu_limit * 100000.0) as i64);
        }

        host_config.binds = Some(binds);

        // Security options
        host_config.security_opt = Some(vec!["no-new-privileges:true".to_string()]);

        Config {
            image: Some(image),
            env: Some(env),
            working_dir: Some("/workspace".to_string()),
            cmd: Some(vec![
                ctx.shell.clone(),
                "-c".to_string(),
                ctx.command.clone(),
            ]),
            host_config: Some(host_config),
            ..Default::default()
        }
    }
}

#[async_trait]
impl Executor for DockerExecutor {
    async fn execute(&self, ctx: &ExecutionContext) -> Result<ExecutionResult> {
        let start = Instant::now();
        let image = ctx.container_image.clone()
            .ok_or_else(|| anyhow::anyhow!("Container image required for Docker executor"))?;

        // Pull image
        self.pull_image(&image).await?;

        // Create container
        let container_name = format!("muelsyse-{}-{}", ctx.job_id, ctx.step_id);
        let config = self.build_container_config(ctx);

        debug!("Creating container: {}", container_name);

        let container = self.docker.create_container(
            Some(CreateContainerOptions {
                name: &container_name,
                platform: None,
            }),
            config,
        ).await.context("Failed to create container")?;

        let container_id = container.id;

        // Start container
        self.docker.start_container(
            &container_id,
            None::<StartContainerOptions<String>>,
        ).await.context("Failed to start container")?;

        debug!("Container started: {}", container_id);

        // Wait for container with timeout
        let wait_result = tokio::time::timeout(
            ctx.timeout,
            async {
                let mut stream = self.docker.wait_container(
                    &container_id,
                    None::<WaitContainerOptions<String>>,
                );

                while let Some(result) = stream.next().await {
                    match result {
                        Ok(response) => {
                            return Ok(response.status_code);
                        }
                        Err(e) => {
                            return Err(anyhow::anyhow!("Wait error: {}", e));
                        }
                    }
                }

                Err(anyhow::anyhow!("Container wait stream ended unexpectedly"))
            }
        ).await;

        // Get logs
        let mut stdout = String::new();
        let mut stderr = String::new();

        let mut log_stream = self.docker.logs(
            &container_id,
            Some(LogsOptions::<String> {
                stdout: true,
                stderr: true,
                ..Default::default()
            }),
        );

        while let Some(result) = log_stream.next().await {
            match result {
                Ok(output) => {
                    match output {
                        bollard::container::LogOutput::StdOut { message } => {
                            stdout.push_str(&String::from_utf8_lossy(&message));
                        }
                        bollard::container::LogOutput::StdErr { message } => {
                            stderr.push_str(&String::from_utf8_lossy(&message));
                        }
                        _ => {}
                    }
                }
                Err(e) => {
                    warn!("Log stream error: {}", e);
                    break;
                }
            }
        }

        // Remove container
        let _ = self.docker.remove_container(
            &container_id,
            Some(RemoveContainerOptions {
                force: true,
                ..Default::default()
            }),
        ).await;

        match wait_result {
            Ok(Ok(exit_code)) => {
                Ok(ExecutionResult {
                    exit_code: exit_code as i32,
                    stdout,
                    stderr,
                    duration: start.elapsed(),
                    timed_out: false,
                })
            }
            Ok(Err(e)) => Err(e),
            Err(_) => {
                // Timeout
                warn!("Container execution timed out");

                // Force stop container
                let _ = self.docker.stop_container(&container_id, None).await;

                Ok(ExecutionResult {
                    exit_code: -1,
                    stdout,
                    stderr: "Container execution timed out".to_string(),
                    duration: start.elapsed(),
                    timed_out: true,
                })
            }
        }
    }

    async fn prepare(&self, ctx: &ExecutionContext) -> Result<()> {
        // Create working directory
        tokio::fs::create_dir_all(&ctx.working_directory)
            .await
            .context("Failed to create working directory")?;

        Ok(())
    }

    async fn cleanup(&self, _ctx: &ExecutionContext) -> Result<()> {
        // Container is already removed after execution
        Ok(())
    }

    async fn health_check(&self) -> Result<bool> {
        self.docker.ping().await?;
        Ok(true)
    }

    fn executor_type(&self) -> ExecutorType {
        ExecutorType::Docker
    }
}
