//! Shared persistence record, independent of the optional Python bridge.

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
