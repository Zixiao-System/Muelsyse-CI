//! System information utilities

use sysinfo::System;

/// System information
#[derive(Debug, Clone)]
pub struct SystemInfo {
    pub os_name: String,
    pub os_version: String,
    pub arch: String,
    pub hostname: String,
    pub cpu_count: usize,
    pub total_memory_mb: u64,
}

/// Get system information
pub fn get_system_info() -> SystemInfo {
    let sys = System::new_all();

    SystemInfo {
        os_name: System::name().unwrap_or_else(|| "Unknown".into()),
        os_version: System::os_version().unwrap_or_else(|| "Unknown".into()),
        arch: std::env::consts::ARCH.to_string(),
        hostname: System::host_name().unwrap_or_else(|| "Unknown".into()),
        cpu_count: sys.cpus().len(),
        total_memory_mb: sys.total_memory() / 1024 / 1024,
    }
}
