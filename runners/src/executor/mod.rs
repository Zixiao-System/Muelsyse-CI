//! Executor module for running jobs

mod traits;
mod shell;
mod docker;

pub use traits::{Executor, ExecutorType, ExecutionContext, ExecutionResult};
pub use shell::ShellExecutor;
pub use docker::DockerExecutor;

use anyhow::Result;
use crate::config::Settings;

/// Create an executor based on type
pub fn create_executor(
    executor_type: ExecutorType,
    settings: &Settings,
) -> Result<Box<dyn Executor>> {
    match executor_type {
        ExecutorType::Shell => Ok(Box::new(ShellExecutor::new(settings.executor.shell.clone()))),
        ExecutorType::Docker => Ok(Box::new(DockerExecutor::new(settings.executor.docker.clone())?)),
    }
}
