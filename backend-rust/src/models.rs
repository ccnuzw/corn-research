//! Domain Models - 领域模型定义

use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc, NaiveDate};
use rust_decimal::Decimal;

/// 采集器状态
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum CollectorStatus {
    Idle,
    Running,
    Failed,
}

/// 采集器信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CollectorInfo {
    pub id: String,
    pub name: String,
    pub status: CollectorStatus,
    pub last_run: Option<DateTime<Utc>>,
    pub last_success: Option<DateTime<Utc>>,
    pub total_runs: u32,
    pub success_rate: f32,
}

/// 采集历史记录
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CollectionHistory {
    pub id: String,
    pub collector_id: String,
    pub started_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
    pub status: String,
    pub records_collected: u32,
    pub error_message: Option<String>,
}

/// 市场数据
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketData {
    pub id: String,
    pub business_date: NaiveDate,
    pub indicator_name: String,
    pub value: f64,
    pub unit: String,
    pub source: String,
    pub quality: String,
    pub collected_at: DateTime<Utc>,
}

/// 定时任务信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScheduledJob {
    pub id: String,
    pub name: String,
    pub collector_id: String,
    pub cron_expr: String,
    pub enabled: bool,
    pub last_run: Option<DateTime<Utc>>,
    pub next_run: Option<DateTime<Utc>>,
    pub status: String,
}

/// 数据统计
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataStats {
    pub total_records: u64,
    pub indicator_count: u64,
    pub coverage_rate: f32,
    pub latest_collection: Option<DateTime<Utc>>,
}

/// 指标信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndicatorInfo {
    pub name: String,
    pub display_name: String,
    pub unit: String,
    pub record_count: u64,
}

/// 质量分数
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualityScore {
    pub indicator: String,
    pub score: f32,
    pub grade: String, // A/B/C/D
    pub issues: Vec<String>,
}

/// 质量分布
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualityDistribution {
    pub grade_a: u32,
    pub grade_b: u32,
    pub grade_c: u32,
    pub grade_d: u32,
}
