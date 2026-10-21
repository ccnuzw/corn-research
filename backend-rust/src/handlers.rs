//! API Handlers - 处理API请求

use axum::{
    Json,
    extract::{Path, Query, State},
    response::IntoResponse,
};
use serde::{Deserialize, Serialize};
use crate::python_bridge;
use crate::errors::CornError;
use crate::models::*;
use crate::AppState;
use chrono::{Utc, Duration, NaiveDate};
use sea_orm::{EntityTrait, QueryFilter, QueryOrder, QuerySelect, ColumnTrait, PaginatorTrait};
use crate::db::entities::{Entity as RawRecords, Column as RawColumn};

#[derive(Serialize)]
pub struct ApiResponse<T> {
    pub success: bool,
    pub data: Option<T>,
    pub message: Option<String>,
}

/// 列出所有采集器
pub async fn list_collectors() -> impl IntoResponse {
    // TODO: 从数据库或配置读取采集器状态
    let collectors = vec![
        CollectorInfo {
            id: "boyar".to_string(),
            name: "博亚和讯".to_string(),
            status: CollectorStatus::Idle,
            last_run: None,
            last_success: None,
            total_runs: 0,
            success_rate: 0.0,
        },
        CollectorInfo {
            id: "sina".to_string(),
            name: "新浪财经".to_string(),
            status: CollectorStatus::Idle,
            last_run: None,
            last_success: None,
            total_runs: 0,
            success_rate: 0.0,
        },
    ];
    
    Json(ApiResponse {
        success: true,
        data: Some(collectors),
        message: None,
    })
}

/// 运行指定采集器
pub async fn run_collector(
    Path(collector_id): Path<String>,
    State(state): State<AppState>,
) -> Result<impl IntoResponse, CornError> {
    tracing::info!("🔄 Running collector: {}", collector_id);
    
    // 发送采集开始通知
    let _ = state.notification_service.notify(
        "采集开始",
        &format!("采集器 {} 开始运行", collector_id),
        "info"
    ).await;
    
    // 调用Python采集器
    let result = python_bridge::run_python_collector(&collector_id).await
        .map_err(|e| CornError::Python(e))?;
    
    // 发送采集完成通知
    let _ = state.notification_service.notify(
        "采集完成",
        &format!("采集器 {} 完成，采集 {} 条记录", collector_id, result.len()),
        "success"
    ).await;
    
    Ok(Json(ApiResponse {
        success: true,
        data: Some(serde_json::json!({
            "collector_id": collector_id,
            "records_collected": result.len(),
        })),
        message: Some(format!("Collected {} records", result.len())),
    }))
}

/// 获取采集器历史记录
#[derive(Deserialize)]
pub struct HistoryQuery {
    pub limit: Option<usize>,
}

pub async fn get_collector_history(
    Path(collector_id): Path<String>,
    Query(query): Query<HistoryQuery>,
) -> impl IntoResponse {
    let _limit = query.limit.unwrap_or(50);
    
    // TODO: 从数据库查询历史记录
    let history: Vec<CollectionHistory> = vec![];
    
    Json(ApiResponse {
        success: true,
        data: Some(history),
        message: None,
    })
}

/// 获取采集器状态
pub async fn get_collector_status(
    Path(collector_id): Path<String>,
) -> impl IntoResponse {
    // TODO: 从Redis或数据库查询实时状态
    let status = CollectorInfo {
        id: collector_id.clone(),
        name: collector_id.clone(),
        status: CollectorStatus::Idle,
        last_run: None,
        last_success: None,
        total_runs: 0,
        success_rate: 0.0,
    };
    
    Json(ApiResponse {
        success: true,
        data: Some(status),
        message: None,
    })
}

// ===== 数据查询API =====

#[derive(Deserialize)]
pub struct LatestDataQuery {
    pub indicator: Option<String>,
    pub days: Option<i32>,
    pub limit: Option<usize>,
}

/// 获取最新数据
pub async fn get_latest_data(
    State(state): State<AppState>,
    Query(query): Query<LatestDataQuery>,
) -> Result<impl IntoResponse, CornError> {
    let days = query.days.unwrap_or(30);
    let limit = query.limit.unwrap_or(100);
    
    tracing::info!("📊 Fetching latest data: days={}, limit={}", days, limit);
    
    // 计算日期范围
    let end_date = Utc::now().naive_utc().date();
    let start_date = end_date - Duration::days(days as i64);
    
    // 从数据库查询
    let mut query_builder = RawRecords::find()
        .filter(RawColumn::BusinessDate.gte(start_date))
        .filter(RawColumn::BusinessDate.lte(end_date))
        .order_by_desc(RawColumn::BusinessDate)
        .order_by_desc(RawColumn::CollectedAt);
    
    // 如果指定了指标，添加过滤
    if let Some(indicator) = query.indicator {
        query_builder = query_builder.filter(RawColumn::IndicatorName.eq(indicator));
    }
    
    let records = query_builder
        .limit(limit as u64)
        .all(&state.db)
        .await
        .map_err(|e| CornError::Internal(format!("Database query failed: {}", e)))?;
    
    // 转换为API模型
    let data: Vec<MarketData> = records.into_iter().map(|r| MarketData {
        id: r.id.to_string(),
        business_date: r.business_date,
        indicator_name: r.indicator_name,
        value: r.value.to_string().parse().unwrap_or(0.0),
        unit: r.unit,
        source: r.collector_id,
        quality: "A".to_string(), // TODO: 计算质量等级
        collected_at: r.collected_at.with_timezone(&Utc),
    }).collect();
    
    tracing::info!("✅ Found {} records", data.len());
    
    Ok(Json(ApiResponse {
        success: true,
        data: Some(data),
        message: None,
    }))
}

/// 获取统计信息
pub async fn get_stats(
    State(state): State<AppState>,
) -> Result<impl IntoResponse, CornError> {
    tracing::info!("📈 Fetching stats");
    
    // 统计总记录数
    let total_records = RawRecords::find()
        .count(&state.db)
        .await
        .map_err(|e| CornError::Internal(format!("Count query failed: {}", e)))?;
    
    // 统计不同指标数量
    let all_records = RawRecords::find()
        .all(&state.db)
        .await
        .map_err(|e| CornError::Internal(format!("Query failed: {}", e)))?;
    
    let mut indicators = std::collections::HashSet::new();
    let mut latest_collection = None;
    
    for record in &all_records {
        indicators.insert(&record.indicator_name);
        if latest_collection.is_none() || record.collected_at > *latest_collection.as_ref().unwrap() {
            latest_collection = Some(record.collected_at);
        }
    }
    
    let stats = DataStats {
        total_records,
        indicator_count: indicators.len() as u64,
        coverage_rate: if indicators.is_empty() { 0.0 } else { 85.5 }, // TODO: 实际计算
        latest_collection: latest_collection.map(|dt| dt.with_timezone(&Utc)),
    };
    
    Ok(Json(ApiResponse {
        success: true,
        data: Some(stats),
        message: None,
    }))
}

#[derive(Deserialize)]
pub struct TrendQuery {
    pub indicator: String,
    pub days: Option<i32>,
}

/// 获取趋势数据
pub async fn get_trend_data(
    State(state): State<AppState>,
    Query(query): Query<TrendQuery>,
) -> Result<impl IntoResponse, CornError> {
    let days = query.days.unwrap_or(30);
    
    tracing::info!("📉 Fetching trend data: indicator={}, days={}", query.indicator, days);
    
    // 计算日期范围
    let end_date = Utc::now().naive_utc().date();
    let start_date = end_date - Duration::days(days as i64);
    
    // 从数据库查询指定指标的数据
    let records = RawRecords::find()
        .filter(RawColumn::IndicatorName.eq(&query.indicator))
        .filter(RawColumn::BusinessDate.gte(start_date))
        .filter(RawColumn::BusinessDate.lte(end_date))
        .order_by_asc(RawColumn::BusinessDate)
        .all(&state.db)
        .await
        .map_err(|e| CornError::Internal(format!("Database query failed: {}", e)))?;
    
    // 转换为API模型
    let data: Vec<MarketData> = records.into_iter().map(|r| MarketData {
        id: r.id.to_string(),
        business_date: r.business_date,
        indicator_name: r.indicator_name,
        value: r.value.to_string().parse().unwrap_or(0.0),
        unit: r.unit,
        source: r.collector_id,
        quality: "A".to_string(),
        collected_at: r.collected_at.with_timezone(&Utc),
    }).collect();
    
    tracing::info!("✅ Found {} trend records", data.len());
    
    Ok(Json(ApiResponse {
        success: true,
        data: Some(data),
        message: None,
    }))
}

/// 获取指标列表
pub async fn get_indicators(
    State(state): State<AppState>,
) -> Result<impl IntoResponse, CornError> {
    tracing::info!("📋 Fetching indicators");
    
    // 查询所有记录并按指标分组
    let all_records = RawRecords::find()
        .all(&state.db)
        .await
        .map_err(|e| CornError::Internal(format!("Query failed: {}", e)))?;
    
    // 按指标名称分组统计
    let mut indicator_map: std::collections::HashMap<String, (String, u64)> = std::collections::HashMap::new();
    
    for record in all_records {
        let entry = indicator_map.entry(record.indicator_name.clone())
            .or_insert((record.unit.clone(), 0));
        entry.1 += 1;
    }
    
    // 转换为API模型
    let indicators: Vec<IndicatorInfo> = indicator_map.into_iter().map(|(name, (unit, count))| {
        IndicatorInfo {
            name: name.clone(),
            display_name: name, // TODO: 添加显示名称映射
            unit,
            record_count: count,
        }
    }).collect();
    
    Ok(Json(ApiResponse {
        success: true,
        data: Some(indicators),
        message: None,
    }))
}

// ===== 数据质量API =====

/// 获取质量分数
pub async fn get_quality_scores() -> Result<impl IntoResponse, CornError> {
    tracing::info!("🎯 Fetching quality scores");
    
    // TODO: 计算质量分数
    let scores: Vec<QualityScore> = vec![];
    
    Ok(Json(ApiResponse {
        success: true,
        data: Some(scores),
        message: None,
    }))
}

/// 获取质量分布
pub async fn get_quality_distribution() -> Result<impl IntoResponse, CornError> {
    tracing::info!("📊 Fetching quality distribution");
    
    // TODO: 计算质量分布
    let distribution = QualityDistribution {
        grade_a: 0,
        grade_b: 0,
        grade_c: 0,
        grade_d: 0,
    };
    
    Ok(Json(ApiResponse {
        success: true,
        data: Some(distribution),
        message: None,
    }))
}

/// 获取问题数据
pub async fn get_quality_issues() -> Result<impl IntoResponse, CornError> {
    tracing::info!("⚠️ Fetching quality issues");
    
    // TODO: 检测并返回问题数据
    let issues: Vec<MarketData> = vec![];
    
    Ok(Json(ApiResponse {
        success: true,
        data: Some(issues),
        message: None,
    }))
}
