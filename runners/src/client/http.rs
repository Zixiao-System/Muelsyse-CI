//! HTTP client for control plane API

use anyhow::{Result, Context};
use reqwest::Client;
use serde::{Serialize, de::DeserializeOwned};

use crate::config::Settings;

/// HTTP client for API calls
pub struct HttpClient {
    client: Client,
    base_url: String,
    token: String,
}

impl HttpClient {
    pub fn new(settings: Settings) -> Self {
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(settings.control_plane.timeout_secs))
            .build()
            .expect("Failed to create HTTP client");

        Self {
            client,
            base_url: settings.control_plane.api_url,
            token: settings.runner.token,
        }
    }

    /// Make a GET request
    pub async fn get<T: DeserializeOwned>(&self, path: &str) -> Result<T> {
        let url = format!("{}{}", self.base_url, path);

        let response = self.client
            .get(&url)
            .header("X-Runner-Token", &self.token)
            .send()
            .await
            .context("HTTP GET request failed")?;

        let status = response.status();
        if !status.is_success() {
            let body = response.text().await.unwrap_or_default();
            anyhow::bail!("API error ({}): {}", status, body);
        }

        response.json().await.context("Failed to parse JSON response")
    }

    /// Make a POST request
    pub async fn post<T: Serialize, R: DeserializeOwned>(&self, path: &str, body: &T) -> Result<R> {
        let url = format!("{}{}", self.base_url, path);

        let response = self.client
            .post(&url)
            .header("X-Runner-Token", &self.token)
            .json(body)
            .send()
            .await
            .context("HTTP POST request failed")?;

        let status = response.status();
        if !status.is_success() {
            let body = response.text().await.unwrap_or_default();
            anyhow::bail!("API error ({}): {}", status, body);
        }

        response.json().await.context("Failed to parse JSON response")
    }

    /// Upload artifact
    pub async fn upload_artifact(&self, path: &str, data: Vec<u8>) -> Result<String> {
        let url = format!("{}/api/v1/artifacts/upload", self.base_url);

        let part = reqwest::multipart::Part::bytes(data)
            .file_name(path.to_string());

        let form = reqwest::multipart::Form::new()
            .part("file", part);

        let response = self.client
            .post(&url)
            .header("X-Runner-Token", &self.token)
            .multipart(form)
            .send()
            .await
            .context("Artifact upload failed")?;

        let status = response.status();
        if !status.is_success() {
            let body = response.text().await.unwrap_or_default();
            anyhow::bail!("Upload error ({}): {}", status, body);
        }

        #[derive(serde::Deserialize)]
        struct UploadResponse {
            storage_path: String,
        }

        let result: UploadResponse = response.json().await?;
        Ok(result.storage_path)
    }
}
