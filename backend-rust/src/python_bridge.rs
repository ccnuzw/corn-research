//! Python桥接模块
//!
//! 通过命令行调用Python采集器

use serde::{Deserialize, Serialize};
use std::process::Command;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawRecord {
    pub business_date: String,
    pub data_type: String,
    pub indicator: String,
    pub value: f64,
    pub unit: String,
    pub region: String,
    pub source_url: String,
    pub original_text: Option<String>,
    pub collected_at: String,
    pub published_at: Option<String>,
    pub metadata: serde_json::Value,
}

#[derive(Debug, Serialize, Deserialize)]
struct CollectorResponse {
    success: bool,
    records: Vec<RawRecord>,
    error: Option<String>,
}

/// 调用Python采集器
pub async fn run_python_collector(
    collector_id: &str,
    max_items: Option<u32>,
) -> Result<Vec<RawRecord>, String> {
    tracing::info!("🐍 Calling Python collector: {}", collector_id);
    
    // 构建Python脚本路径
    let script_path = PathBuf::from("/app/collectors-python/run_collector.py");
    
    // 如果在开发环境，使用相对路径
    let script_path = if script_path.exists() {
        script_path
    } else {
        PathBuf::from("collectors-python/run_collector.py")
    };
    
    if !script_path.exists() {
        return Err(format!("Python script not found: {:?}", script_path));
    }
    
    // 构建命令参数
    let mut args = vec![
        script_path.to_str().unwrap().to_string(),
        "--collector".to_string(),
        collector_id.to_string(),
        "--format".to_string(),
        "json".to_string(),
    ];
    
    if let Some(max) = max_items {
        args.push("--max-items".to_string());
        args.push(max.to_string());
    }
    
    // 执行Python命令
    let output = tokio::task::spawn_blocking(move || {
        Command::new("python3")
            .args(&args)
            .output()
    })
    .await
    .map_err(|e| format!("Failed to spawn Python process: {}", e))?
    .map_err(|e| format!("Failed to execute Python script: {}", e))?;
    
    // 检查执行状态
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        tracing::error!("Python collector failed: {}", stderr);
        return Err(format!("Python collector failed: {}", stderr));
    }
    
    // 解析JSON输出
    let stdout = String::from_utf8_lossy(&output.stdout);
    let response: CollectorResponse = serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse collector response: {}", e))?;
    
    if !response.success {
        return Err(response.error.unwrap_or_else(|| "Unknown error".to_string()));
    }
    
    tracing::info!("✅ Collected {} records from {}", response.records.len(), collector_id);
    Ok(response.records)
}

/// 列出可用的采集器
pub async fn list_available_collectors() -> Result<Vec<String>, String> {
    let script_path = PathBuf::from("/app/collectors-python/run_collector.py");
    let script_path = if script_path.exists() {
        script_path
    } else {
        PathBuf::from("collectors-python/run_collector.py")
    };
    
    if !script_path.exists() {
        return Ok(vec![
            "boyar_production".to_string(),
            "sina_production".to_string(),
            "mock".to_string(),
        ]);
    }
    
    let output = tokio::task::spawn_blocking(move || {
        Command::new("python3")
            .args(&[
                script_path.to_str().unwrap(),
                "--list",
            ])
            .output()
    })
    .await
    .map_err(|e| format!("Failed to spawn process: {}", e))?
    .map_err(|e| format!("Failed to execute script: {}", e))?;
    
    if !output.status.success() {
        return Ok(vec![
            "boyar_production".to_string(),
            "sina_production".to_string(),
            "mock".to_string(),
        ]);
    }
    
    let stdout = String::from_utf8_lossy(&output.stdout);
    let collectors: Vec<String> = serde_json::from_str(&stdout)
        .unwrap_or_else(|_| vec![
            "boyar_production".to_string(),
            "sina_production".to_string(),
            "mock".to_string(),
        ]);
    
    Ok(collectors)
}
