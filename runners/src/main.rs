//! Muelsyse Runner Entry Point
//!
//! Features:
//! - Graceful shutdown on SIGINT/SIGTERM
//! - Wait for running jobs before exit
//! - Notify control plane on shutdown

use anyhow::Result;
use std::sync::Arc;
use tokio::sync::broadcast;
use tracing::{info, error, warn};
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

/// Application state for shutdown coordination
struct AppState {
    settings: Settings,
    shutdown_tx: broadcast::Sender<()>,
}

impl AppState {
    fn new(settings: Settings) -> Self {
        let (shutdown_tx, _) = broadcast::channel(1);
        Self {
            settings,
            shutdown_tx,
        }
    }

    fn shutdown_sender(&self) -> broadcast::Sender<()> {
        self.shutdown_tx.clone()
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new(
            std::env::var("RUST_LOG").unwrap_or_else(|_| "info".into()),
        ))
        .with(tracing_subscriber::fmt::layer())
        .init();

    info!("Starting Muelsyse Runner v{}...", env!("CARGO_PKG_VERSION"));

    // Load configuration
    let settings = Settings::load()?;
    info!("Loaded configuration for runner: {}", settings.runner.name);
    info!("Runner ID: {}", settings.runner.id);
    info!("Control plane: {}", settings.control_plane.ws_url);

    // Create application state
    let app_state = Arc::new(AppState::new(settings.clone()));

    // Setup signal handlers
    let shutdown_tx = app_state.shutdown_sender();
    setup_signal_handlers(shutdown_tx.clone());

    // Create control plane client
    let client = ControlPlaneClient::new(settings.clone());

    // Create job runner with shutdown channel
    let runner = JobRunner::new(settings.clone(), client);

    // Connect runner's shutdown to our signal handler
    let runner_shutdown = runner.shutdown_sender();
    let mut app_shutdown_rx = shutdown_tx.subscribe();

    // Spawn task to forward shutdown signal to runner
    tokio::spawn(async move {
        if app_shutdown_rx.recv().await.is_ok() {
            let _ = runner_shutdown.send(());
        }
    });

    // Run the main loop
    let result = runner.run().await;

    // Notify control plane that runner is going offline
    notify_offline(&settings).await;

    match result {
        Ok(_) => {
            info!("Runner shutdown complete");
            Ok(())
        }
        Err(e) => {
            error!("Runner error: {}", e);
            Err(e)
        }
    }
}

/// Setup signal handlers for graceful shutdown
fn setup_signal_handlers(shutdown_tx: broadcast::Sender<()>) {
    // Handle SIGINT (Ctrl+C)
    let shutdown_tx_int = shutdown_tx.clone();
    tokio::spawn(async move {
        match tokio::signal::ctrl_c().await {
            Ok(()) => {
                info!("Received SIGINT, initiating graceful shutdown...");
                let _ = shutdown_tx_int.send(());
            }
            Err(e) => {
                error!("Failed to listen for SIGINT: {}", e);
            }
        }
    });

    // Handle SIGTERM (Unix only)
    #[cfg(unix)]
    {
        let shutdown_tx_term = shutdown_tx.clone();
        tokio::spawn(async move {
            let mut sigterm = match tokio::signal::unix::signal(
                tokio::signal::unix::SignalKind::terminate()
            ) {
                Ok(s) => s,
                Err(e) => {
                    error!("Failed to register SIGTERM handler: {}", e);
                    return;
                }
            };

            sigterm.recv().await;
            info!("Received SIGTERM, initiating graceful shutdown...");
            let _ = shutdown_tx_term.send(());
        });

        // Handle SIGHUP (reload config - future feature)
        let shutdown_tx_hup = shutdown_tx;
        tokio::spawn(async move {
            let mut sighup = match tokio::signal::unix::signal(
                tokio::signal::unix::SignalKind::hangup()
            ) {
                Ok(s) => s,
                Err(e) => {
                    warn!("Failed to register SIGHUP handler: {}", e);
                    return;
                }
            };

            loop {
                sighup.recv().await;
                info!("Received SIGHUP, graceful shutdown requested...");
                // In future, this could trigger config reload
                // For now, treat as shutdown
                let _ = shutdown_tx_hup.send(());
                break;
            }
        });
    }
}

/// Notify control plane that runner is going offline
async fn notify_offline(settings: &Settings) {
    info!("Notifying control plane of runner shutdown...");

    let client = ControlPlaneClient::new(settings.clone());

    match client.connect_websocket().await {
        Ok(ws) => {
            if let Err(e) = ws.send_offline_notification(
                &settings.runner.id,
                "Graceful shutdown",
            ).await {
                warn!("Failed to send offline notification: {}", e);
            } else {
                info!("Offline notification sent successfully");
            }

            // Give some time for the message to be sent
            tokio::time::sleep(std::time::Duration::from_millis(500)).await;

            if let Err(e) = ws.close().await {
                warn!("Error closing WebSocket: {}", e);
            }
        }
        Err(e) => {
            warn!("Could not connect to notify offline status: {}", e);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_shutdown_broadcast() {
        let (tx, mut rx1) = broadcast::channel::<()>(1);
        let mut rx2 = tx.subscribe();

        tx.send(()).unwrap();

        assert!(rx1.recv().await.is_ok());
        assert!(rx2.recv().await.is_ok());
    }
}
