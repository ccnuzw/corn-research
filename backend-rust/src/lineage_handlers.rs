//! 数据血统API处理器

use axum::{
    extract::{State, Path},
    Json,
    response::IntoResponse,
};
use serde::{Deserialize, Serialize};
use sea_orm::EntityTrait;

use crate::{AppState, ApiResponse};
use crate::standardization::StandardEntity;

#[derive(Serialize)]
struct LineageResponse {
    standard_record: serde_json::Value,
    raw_record: serde_json::Value,
    lineage_chain: Vec<String>,
}

pub async fn get_data_lineage(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> impl IntoResponse {
    let uuid = match uuid::Uuid::parse_str(&id) {
        Ok(u) => u,
        Err(e) => return Json(ApiResponse::<LineageResponse> {
            success: false,
            data: None,
            message: Some(format!("Invalid UUID: {}", e)),
        }),
    };
    
    // 查找STANDARD记录
    let standard_record = match StandardEntity::find_by_id(uuid)
        .one(&state.db)
        .await
    {
        Ok(Some(record)) => record,
        Ok(None) => return Json(ApiResponse {
            success: false,
            data: None,
            message: Some("Record not found".to_string()),
        }),
        Err(e) => return Json(ApiResponse {
            success: false,
            data: None,
            message: Some(format!("Database error: {}", e)),
        }),
    };
    
    // 查找关联的RAW记录
    let raw_record = if let Some(raw_id) = standard_record.raw_record_id {
        match crate::db::entities::Entity::find_by_id(raw_id)
            .one(&state.db)
            .await
        {
            Ok(Some(record)) => Some(record),
            _ => None,
        }
    } else {
        None
    };
    
    // 构建血统链
    let mut lineage_chain = vec![
        format!("采集: {} ({})", 
            standard_record.source_id, 
            standard_record.collected_at.format("%Y-%m-%d %H:%M")),
        format!("标准化: {} (质量等级: {})", 
            standard_record.standardized_at.format("%Y-%m-%d %H:%M"),
            standard_record.quality_grade),
        format!("版本: {}", standard_record.version),
    ];
    
    if let Some(ref raw) = raw_record {
        lineage_chain.insert(0, format!("原始记录: {}", raw.dedup_key));
    }
    
    Json(ApiResponse {
        success: true,
        data: Some(LineageResponse {
            standard_record: serde_json::to_value(&standard_record).unwrap(),
            raw_record: serde_json::to_value(&raw_record).unwrap(),
            lineage_chain,
        }),
        message: None,
    })
}

#[derive(Deserialize)]
pub struct StandardizeRequest {
    pub raw_record_ids: Vec<String>,
}

pub async fn trigger_standardization(
    State(state): State<AppState>,
    Json(req): Json<StandardizeRequest>,
) -> impl IntoResponse {
    let mut success_count = 0;
    let mut error_count = 0;
    
    for raw_id_str in req.raw_record_ids {
        let uuid = match uuid::Uuid::parse_str(&raw_id_str) {
            Ok(u) => u,
            Err(_) => {
                error_count += 1;
                continue;
            }
        };
        
        // 查找RAW记录
        let raw_record = match crate::db::entities::Entity::find_by_id(uuid)
            .one(&state.db)
            .await
        {
            Ok(Some(record)) => record,
            _ => {
                error_count += 1;
                continue;
            }
        };
        
        // 标准化
        match state.standardization_service.standardize_raw_record(&raw_record).await {
            Ok(_) => success_count += 1,
            Err(_) => error_count += 1,
        }
    }
    
    Json(ApiResponse {
        success: true,
        data: Some(serde_json::json!({
            "success_count": success_count,
            "error_count": error_count,
        })),
        message: Some(format!("Standardized {} records", success_count)),
    })
}

pub async fn trigger_auto_promotion(
    State(state): State<AppState>,
) -> impl IntoResponse {
    match state.standardization_service.auto_promote_quality_data().await {
        Ok(count) => Json(ApiResponse {
            success: true,
            data: Some(serde_json::json!({
                "promoted_count": count,
            })),
            message: Some(format!("Auto-promoted {} records", count)),
        }),
        Err(e) => Json(ApiResponse {
            success: false,
            data: Some(serde_json::json!({
                "promoted_count": 0,
            })),
            message: Some(format!("Auto-promotion failed: {}", e)),
        }),
    }
}
