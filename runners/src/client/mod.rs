//! Control plane client

mod websocket;
mod http;

pub use websocket::WebSocketClient;
pub use http::HttpClient;

use crate::config::Settings;

/// Client for communicating with the control plane
pub struct ControlPlaneClient {
    settings: Settings,
    http: HttpClient,
}

impl ControlPlaneClient {
    pub fn new(settings: Settings) -> Self {
        let http = HttpClient::new(settings.clone());
        Self { settings, http }
    }

    /// Create a new WebSocket connection
    pub async fn connect_websocket(&self) -> anyhow::Result<WebSocketClient> {
        WebSocketClient::connect(self.settings.clone()).await
    }

    /// Get the HTTP client
    pub fn http(&self) -> &HttpClient {
        &self.http
    }
}
