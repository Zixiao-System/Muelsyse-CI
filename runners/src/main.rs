//! Muelsyse Runner Entry Point

use anyhow::Result;
use tracing::{info, error};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

mod config;
mod client;
mod executor;
mod job;
mod log;
mod artifact;
mod utils;

use config::Settings;
use client::ControlPlaneClient;
use job::JobRunner;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new(
            std::env::var("RUST_LOG").unwrap_or_else(|_| "info".into()),
        ))
        .with(tracing_subscriber::fmt::layer())
        .init();

    info!("Starting Muelsyse Runner...");

    // Load configuration
    let settings = Settings::load()?;
    info!("Loaded configuration for runner: {}", settings.runner.name);

    // Create control plane client
    let client = ControlPlaneClient::new(settings.clone());

    // Create job runner
    let runner = JobRunner::new(settings.clone(), client);

    // Run the main loop
    if let Err(e) = runner.run().await {
        error!("Runner error: {}", e);
        return Err(e);
    }

    info!("Runner shutdown complete");
    Ok(())
}
