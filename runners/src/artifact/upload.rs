//! Artifact upload utilities

use anyhow::{Result, Context};
use sha2::{Sha256, Digest};
use std::path::Path;
use tokio::fs::File;
use tokio::io::AsyncReadExt;

/// Artifact uploader
pub struct ArtifactUploader {
    base_path: std::path::PathBuf,
}

impl ArtifactUploader {
    pub fn new(base_path: std::path::PathBuf) -> Self {
        Self { base_path }
    }

    /// Calculate SHA256 checksum of a file
    pub async fn calculate_checksum(path: &Path) -> Result<String> {
        let mut file = File::open(path).await
            .context("Failed to open file for checksum")?;

        let mut hasher = Sha256::new();
        let mut buffer = vec![0u8; 8192];

        loop {
            let bytes_read = file.read(&mut buffer).await?;
            if bytes_read == 0 {
                break;
            }
            hasher.update(&buffer[..bytes_read]);
        }

        Ok(hex::encode(hasher.finalize()))
    }

    /// Get file size
    pub async fn get_file_size(path: &Path) -> Result<u64> {
        let metadata = tokio::fs::metadata(path).await
            .context("Failed to get file metadata")?;
        Ok(metadata.len())
    }

    /// Read file contents
    pub async fn read_file(path: &Path) -> Result<Vec<u8>> {
        tokio::fs::read(path).await
            .context("Failed to read file")
    }
}
