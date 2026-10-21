//! Python桥接模块
//!
//! 从Rust调用Python采集器

// 暂时禁用PyO3，定义RawRecord结构用于mock数据
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawRecord {
    pub business_date: String,
    pub indicator_name: String,
    pub value: f64,
    pub unit: String,
    pub region: Option<String>,
    pub source_url: String,
    pub original_text: Option<String>,
    pub collector_id: String,
    pub collected_at: String,
}

/// 调用Python采集器（暂时返回mock数据，避免PyO3链接问题）
pub async fn run_python_collector(collector_id: &str) -> Result<Vec<RawRecord>, String> {
    tracing::warn!("⚠️ Using mock collector data (PyO3 linking disabled)");
    
    // 返回mock数据
    Ok(vec![
        RawRecord {
            collector_id: collector_id.to_string(),
            business_date: "2026-10-21".to_string(),
            indicator_name: "corn_price".to_string(),
            value: 2850.0,
            unit: "元/吨".to_string(),
            region: Some("山东".to_string()),
            source_url: "https://example.com".to_string(),
            original_text: Some("mock data".to_string()),
            collected_at: chrono::Utc::now().to_rfc3339(),
        }
    ])
}
