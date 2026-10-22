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
    #[serde(default)]
    cursor_updates: Vec<serde_json::Value>,
}

pub struct CollectorBatch {
    pub records: Vec<RawRecord>,
    pub cursor_updates: Vec<serde_json::Value>,
}

/// 调用Python采集器
pub async fn run_python_collector(
    collector_id: &str,
    max_items: Option<u32>,
) -> Result<Vec<RawRecord>, String> {
    run_python_collector_with_progress(collector_id, max_items, None).await.map(|batch| batch.records)
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProgressEvent {
    pub phase: String,
    #[serde(default)]
    pub completed: u32,
    #[serde(default)]
    pub total: u32,
    #[serde(flatten)]
    pub details: serde_json::Map<String, serde_json::Value>,
}

pub async fn run_python_collector_with_progress(
    collector_id: &str, max_items: Option<u32>,
    progress: Option<tokio::sync::mpsc::UnboundedSender<ProgressEvent>>,
) -> Result<CollectorBatch, String> {
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
        "--collector".to_string(),
        collector_id.to_string(),
        "--format".to_string(),
        "json".to_string(),
    ];
    
    if let Some(max) = max_items {
        args.push("--max-items".to_string());
        args.push(max.to_string());
    }
    
    let output = if let Some(sender) = progress {
        use std::process::Stdio;
        use tokio::io::{AsyncBufReadExt, AsyncReadExt, BufReader};
        let mut child = tokio::process::Command::new("python3")
            .arg(script_path).args(&args).env("CORN_PROGRESS_ENABLED", "1")
            .stdout(Stdio::piped()).stderr(Stdio::piped()).kill_on_drop(true)
            .spawn().map_err(|e| format!("Failed to start Python: {}", e))?;
        let mut stdout = child.stdout.take().ok_or("Missing Python stdout")?;
        let stderr = child.stderr.take().ok_or("Missing Python stderr")?;
        let reader = tokio::spawn(async move {
            let mut bytes = Vec::new();
            stdout.read_to_end(&mut bytes).await.map(|_| bytes)
        });
        let process = async {
            let mut lines = BufReader::new(stderr).lines();
            let mut diagnostics = String::new();
            while let Some(line) = lines.next_line().await.map_err(|e| e.to_string())? {
                if let Some(json) = line.strip_prefix("CORN_PROGRESS ") {
                    match serde_json::from_str::<ProgressEvent>(json) {
                        Ok(event) => { let _ = sender.send(event); }
                        Err(e) => tracing::warn!(error=%e, "Malformed collector progress ignored"),
                    }
                } else {
                    tracing::debug!(collector_id, line, "Python collector log");
                    diagnostics.push_str(&line);
                    diagnostics.push('\n');
                    if diagnostics.len() > 32768 { diagnostics = diagnostics.chars().rev().take(16384).collect::<String>().chars().rev().collect(); }
                }
            }
            let status = child.wait().await.map_err(|e| e.to_string())?;
            let stdout = reader.await.map_err(|e| e.to_string())?.map_err(|e| e.to_string())?;
            Ok::<_, String>(std::process::Output { status, stdout, stderr: diagnostics.into_bytes() })
        };
        tokio::time::timeout(std::time::Duration::from_secs(7200), process).await
            .map_err(|_| "Collector exceeded two-hour execution limit".to_string())??
    } else {
        tokio::task::spawn_blocking(move || {
            Command::new("python3").arg(script_path).args(&args).output()
        }).await.map_err(|e| format!("Failed to spawn Python process: {}", e))?
          .map_err(|e| format!("Failed to execute Python script: {}", e))?
    };

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
        tracing::warn!(collector_id, stderr = %String::from_utf8_lossy(&output.stderr),
            "Python collector reported failure");
        return Err(response.error.unwrap_or_else(|| "Unknown error".to_string()));
    }

    tracing::info!(collector_id, stderr = %String::from_utf8_lossy(&output.stderr),
        "Python collector diagnostics");
    
    tracing::info!("✅ Collected {} records from {}", response.records.len(), collector_id);
    Ok(CollectorBatch { records: response.records, cursor_updates: response.cursor_updates })
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
            .arg(script_path)
            .arg("--list")
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

/// Acknowledge Redis checkpoints only after the database accepted every observation.
pub async fn commit_cursor_updates(updates: Vec<serde_json::Value>) -> Result<(), String> {
    if updates.is_empty() { return Ok(()); }
    let payload = serde_json::to_vec(&updates).map_err(|e| e.to_string())?;
    let script = if PathBuf::from("/app/collectors-python/commit_cursors.py").exists() {
        PathBuf::from("/app/collectors-python/commit_cursors.py")
    } else { PathBuf::from("collectors-python/commit_cursors.py") };
    let output = tokio::task::spawn_blocking(move || {
        use std::io::Write;
        let mut child = Command::new("python3").arg(script)
            .stdin(std::process::Stdio::piped()).stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped()).spawn().map_err(|e| e.to_string())?;
        child.stdin.take().ok_or("Missing cursor commit stdin")?
            .write_all(&payload).map_err(|e| e.to_string())?;
        child.wait_with_output().map_err(|e| e.to_string())
    }).await.map_err(|e| e.to_string())??;
    if !output.status.success() {
        return Err(format!("Cursor acknowledgement failed after persistence: {} {}",
            String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr)));
    }
    Ok(())
}
