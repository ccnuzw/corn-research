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
        CollectorInfo {
            id: "dce".to_string(),
            name: "大连商品交易所".to_string(),
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
) -> Result<Json<ApiResponse<serde_json::Value>>, CornError> {
    execute_collector(collector_id, state, 100).await
}

#[derive(Deserialize)]
pub struct RunCollectorRequest {
    #[serde(alias = "collector_id")]
    pub collector_name: String,
    pub max_items: Option<u32>,
}

impl RunCollectorRequest {
    fn validate(&self) -> Result<(), CornError> {
        if self.collector_name.trim().is_empty() {
            return Err(CornError::Validation("collector_name must not be empty".into()));
        }
        if self.max_items == Some(0) {
            return Err(CornError::Validation("max_items must be positive".into()));
        }
        Ok(())
    }
}

pub async fn run_collector_by_name(
    State(state): State<AppState>,
    Json(request): Json<RunCollectorRequest>,
) -> Result<Json<ApiResponse<serde_json::Value>>, CornError> {
    request.validate()?;
    execute_collector(request.collector_name, state, request.max_items.unwrap_or(100)).await
}

async fn execute_collector(
    collector_id: String,
    state: AppState,
    max_items: u32,
) -> Result<Json<ApiResponse<serde_json::Value>>, CornError> {
    let available = python_bridge::list_available_collectors().await
        .map_err(CornError::Python)?;
    if !available.contains(&collector_id) {
        return Err(CornError::Validation(format!("Unknown collector: {}", collector_id)));
    }
    tracing::info!("🔄 Running collector: {}", collector_id);
    
    // 发送采集开始通知
    let _ = state.notification_service.notify(
        "采集开始",
        &format!("采集器 {} 开始运行", collector_id),
        "info"
    ).await;
    
    let adapter = crate::collection_execution::resolve_adapter(&state.db, &collector_id).await
        .map_err(CornError::Validation)?;
    let history = crate::collection_execution::start_run(&state.db, &adapter.id).await
        .map_err(|e| CornError::Internal(e.to_string()))?;
    let run_id = history.id.clone();
    let db = state.db.clone();
    let persist = matches!(adapter.script_file.as_str(), "sina_production" | "dce_production");
    // Keep finalization alive if the HTTP client disconnects mid-collection.
    let count = tokio::spawn(crate::collection_execution::execute_run(
        db, adapter, history, max_items, persist,
    )).await.map_err(|e| CornError::Internal(e.to_string()))?
        .map_err(CornError::Python)?;
    
    // 发送采集完成通知
    let _ = state.notification_service.notify(
        "采集完成",
        &format!("采集器 {} 完成，采集 {} 条记录", collector_id, count),
        "success"
    ).await;
    
    Ok(Json(ApiResponse {
        success: true,
        data: Some(serde_json::json!({
            "collector_id": collector_id,
            "records_collected": count,
            "run_id": run_id,
        })),
        message: Some(format!("Collected {} records", count)),
    }))
}

/// 获取采集器历史记录
#[derive(Deserialize)]
pub struct HistoryQuery {
    pub limit: Option<usize>,
}

pub async fn get_collector_history(
    Path(collector_id): Path<String>,
    State(state): State<AppState>,
    Query(query): Query<HistoryQuery>,
) -> Result<impl IntoResponse, CornError> {
    use crate::db::collection_entities::run;
    let limit = query.limit.unwrap_or(50);
    if !(1..=100).contains(&limit) {
        return Err(CornError::Validation("limit must be between 1 and 100".into()));
    }
    let adapter = crate::collection_execution::resolve_adapter(&state.db, &collector_id).await
        .map_err(CornError::Validation)?;
    let runs = run::Entity::find().filter(run::Column::AdapterId.eq(adapter.id))
        .order_by_desc(run::Column::StartedAt).order_by_desc(run::Column::Id)
        .limit(limit as u64).all(&state.db).await
        .map_err(|e| CornError::Internal(e.to_string()))?;
    let history: Vec<CollectionHistory> = runs.into_iter().map(|r| CollectionHistory {
        id: r.id, collector_id: collector_id.clone(),
        started_at: r.started_at.with_timezone(&Utc),
        completed_at: r.completed_at.map(|t| t.with_timezone(&Utc)),
        status: r.status.unwrap_or_else(|| "unknown".into()),
        records_collected: r.records_collected.max(0) as u32,
        error_message: r.error_message,
    }).collect();
    
    Ok(Json(ApiResponse {
        success: true,
        data: Some(history),
        message: None,
    }))
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
    pub topic: Option<String>,
    pub indicator: Option<String>,
    pub days: Option<i32>,
    pub limit: Option<usize>,
}

fn topic_indicators(topic: &str) -> Vec<&str> {
    match topic {
        "shandong_arrivals" | "corn_arrivals" => vec!["山东到车量", "山东深加工到车量"],
        "corn_spot_price" => vec!["玉米现货价格"],
        "corn_futures_price" => vec!["玉米期货价格"],
        "north_port_inventory" => vec!["北方四港库存"],
        "north_port_shipping" => vec!["北方四港下海量"],
        _ => vec![topic],
    }
}

fn latest_records_query(query: &LatestDataQuery, end_date: NaiveDate) -> sea_orm::Select<RawRecords> {
    let start_date = end_date.checked_sub_signed(Duration::days(query.days.unwrap_or(30) as i64))
        .unwrap_or(NaiveDate::MIN);
    let mut records = RawRecords::find()
        .filter(RawColumn::BusinessDate.gte(start_date))
        .filter(RawColumn::BusinessDate.lte(end_date))
        .order_by_desc(RawColumn::BusinessDate)
        .order_by_desc(RawColumn::CollectedAt);
    if let Some(topic) = &query.topic {
        // Legacy raw records store indicator names, not topic identifiers.
        records = records.filter(RawColumn::IndicatorName.is_in(topic_indicators(topic)));
    }
    if let Some(indicator) = &query.indicator {
        records = records.filter(RawColumn::IndicatorName.eq(indicator));
    }
    records.limit(query.limit.unwrap_or(100) as u64)
}

/// 获取最新数据
pub async fn get_latest_data(
    State(state): State<AppState>,
    Query(query): Query<LatestDataQuery>,
) -> Result<impl IntoResponse, CornError> {
    let days = query.days.unwrap_or(30);
    if !(1..=36500).contains(&days) || !(1..=10000).contains(&query.limit.unwrap_or(100)) {
        return Err(CornError::Validation("days must be 1..36500 and limit must be 1..10000".into()));
    }
    let limit = query.limit.unwrap_or(100);
    
    tracing::info!("📊 Fetching latest data: days={}, limit={}", days, limit);
    
    let end_date = Utc::now().naive_utc().date();
    let records = latest_records_query(&query, end_date)
        .all(&state.db)
        .await
        .map_err(|e| CornError::Internal(format!("Database query failed: {}", e)))?;
    
    // 转换为API模型
    let data: Vec<MarketData> = records.into_iter().map(|r| -> Result<MarketData, CornError> { Ok(MarketData {
        id: r.id.to_string(),
        business_date: r.business_date,
        indicator_name: r.indicator_name,
        value: r.value.to_string().parse::<f64>()
            .map_err(|e| CornError::Internal(format!("Invalid stored numeric value: {}", e)))?,
        unit: r.unit,
        source: r.collector_id,
        quality: "A".to_string(), // TODO: 计算质量等级
        collected_at: r.collected_at.with_timezone(&Utc),
    }) }).collect::<Result<_, _>>()?;
    
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
    let latest_collection = all_records.iter().map(|record| record.collected_at).max();
    
    for record in &all_records {
        indicators.insert(&record.indicator_name);
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
    if !(1..=36500).contains(&days) {
        return Err(CornError::Validation("days must be 1..36500".into()));
    }
    let start_date = end_date.checked_sub_signed(Duration::days(days as i64))
        .ok_or_else(|| CornError::Validation("Date range exceeds supported dates".into()))?;
    
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
    let data: Vec<MarketData> = records.into_iter().map(|r| -> Result<MarketData, CornError> { Ok(MarketData {
        id: r.id.to_string(),
        business_date: r.business_date,
        indicator_name: r.indicator_name,
        value: r.value.to_string().parse::<f64>()
            .map_err(|e| CornError::Internal(format!("Invalid stored numeric value: {}", e)))?,
        unit: r.unit,
        source: r.collector_id,
        quality: "A".to_string(),
        collected_at: r.collected_at.with_timezone(&Utc),
    }) }).collect::<Result<_, _>>()?;
    
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
    
    // TODO: 从数据库实际查询质量分布
    // 当前返回空数据，等待STANDARD层有数据后实现
    let distribution = QualityDistribution {
        grade_a: 0,
        grade_b: 0,
        grade_c: 0,
        grade_d: 0,
        grade_m: 0,  // Mock数据计数
    };
    
    Ok(Json(ApiResponse {
        success: true,
        data: Some(distribution),
        message: Some("质量分布统计(M=Mock测试数据)".to_string()),
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

#[cfg(test)]
mod api_regression_tests {
    use super::*;
    use sea_orm::{DbBackend, QueryTrait};

    fn sql(params: serde_json::Value) -> String {
        let query: LatestDataQuery = serde_json::from_value(params).unwrap();
        latest_records_query(&query, NaiveDate::from_ymd_opt(2026, 10, 22).unwrap())
            .build(DbBackend::Postgres).to_string()
    }

    #[test]
    fn collector_request_supports_both_names() {
        for field in ["collector_name", "collector_id"] {
            let request: RunCollectorRequest = serde_json::from_value(
                serde_json::json!({field: "boyar_production", "max_items": 5})
            ).unwrap();
            assert_eq!(request.collector_name, "boyar_production");
            assert_eq!(request.max_items, Some(5));
            assert!(request.validate().is_ok());
        }
    }

    #[test]
    fn collector_request_rejects_invalid_input() {
        for value in [
            serde_json::json!({"collector_name": " "}),
            serde_json::json!({"collector_name": "mock", "max_items": 0}),
        ] {
            let request: RunCollectorRequest = serde_json::from_value(value).unwrap();
            assert!(request.validate().is_err());
        }
        assert!(serde_json::from_value::<RunCollectorRequest>(serde_json::json!({})).is_err());
    }

    #[test]
    fn arrivals_topic_filters_both_legacy_indicators_in_sql() {
        let statement = sql(serde_json::json!({"topic": "shandong_arrivals"}));
        assert!(statement.contains("\"indicator_name\" IN ('山东到车量', '山东深加工到车量')"));
        assert_eq!(statement, sql(serde_json::json!({"topic": "corn_arrivals"})));
    }

    #[test]
    fn unknown_topic_is_filtered_not_ignored() {
        let statement = sql(serde_json::json!({"topic": "missing_topic"}));
        assert!(statement.contains("\"indicator_name\" IN ('missing_topic')"));
    }

    #[test]
    fn topic_and_indicator_filters_are_combined() {
        let statement = sql(serde_json::json!({
            "topic": "north_port_inventory", "indicator": "北方四港库存", "days": 7, "limit": 2
        }));
        assert!(statement.contains("\"indicator_name\" IN ('北方四港库存')"));
        assert!(statement.contains("AND \"raw_collection_records\".\"indicator_name\" = '北方四港库存'"));
        assert!(statement.contains("2026-10-15"));
        assert!(statement.ends_with("LIMIT 2"));
    }

    #[test]
    fn unfiltered_query_keeps_default_date_and_limit() {
        let statement = sql(serde_json::json!({}));
        assert!(!statement.contains("\"indicator_name\" IN"));
        assert!(statement.contains("2026-09-22"));
        assert!(statement.ends_with("LIMIT 100"));
    }
}
