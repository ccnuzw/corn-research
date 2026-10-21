//! Collection Management API Handlers

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    Json,
};
use sea_orm::{
    ActiveModelTrait, ColumnTrait, EntityTrait, PaginatorTrait, QueryFilter,
    QueryOrder, QuerySelect, Set, IntoActiveModel,
};
use serde::{Deserialize, Serialize};
use chrono::Utc;
use uuid::Uuid;

use crate::AppState;
use crate::db::collection_entities::{
    self,
    adapter,
    record,
    run,
    Entity as SourceEntity,
    Model as SourceModel,
    ActiveModel as SourceActiveModel,
    Column as SourceColumn,
};

#[derive(Serialize)]
pub struct ApiResponse<T> {
    pub success: bool,
    pub data: Option<T>,
    pub message: Option<String>,
}

// ===== 数据源管理 =====

#[derive(Deserialize)]
pub struct CreateSourceRequest {
    pub id: String,
    pub name: String,
    pub domain: Option<String>,
    pub description: Option<String>,
}

pub async fn list_sources(
    State(state): State<AppState>,
) -> Result<Json<ApiResponse<Vec<SourceModel>>>, StatusCode> {
    match SourceEntity::find()
        .order_by_asc(SourceColumn::Name)
        .all(&state.db)
        .await
    {
        Ok(sources) => Ok(Json(ApiResponse {
            success: true,
            data: Some(sources),
            message: None,
        })),
        Err(e) => {
            tracing::error!("Failed to list sources: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

pub async fn get_source(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<ApiResponse<SourceModel>>, StatusCode> {
    match SourceEntity::find_by_id(id).one(&state.db).await {
        Ok(Some(source)) => Ok(Json(ApiResponse {
            success: true,
            data: Some(source),
            message: None,
        })),
        Ok(None) => Err(StatusCode::NOT_FOUND),
        Err(e) => {
            tracing::error!("Failed to get source: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

pub async fn create_source(
    State(state): State<AppState>,
    Json(req): Json<CreateSourceRequest>,
) -> Result<Json<ApiResponse<SourceModel>>, StatusCode> {
    let source = SourceActiveModel {
        id: Set(req.id),
        name: Set(req.name),
        domain: Set(req.domain),
        description: Set(req.description),
        status: Set("active".to_string()),
        ..Default::default()
    };

    match source.insert(&state.db).await {
        Ok(model) => Ok(Json(ApiResponse {
            success: true,
            data: Some(model),
            message: Some("Source created successfully".to_string()),
        })),
        Err(e) => {
            tracing::error!("Failed to create source: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

#[derive(Deserialize)]
pub struct UpdateSourceRequest {
    pub name: Option<String>,
    pub domain: Option<String>,
    pub description: Option<String>,
    pub status: Option<String>,
}

pub async fn update_source(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Json(req): Json<UpdateSourceRequest>,
) -> Result<Json<ApiResponse<SourceModel>>, StatusCode> {
    let source = match SourceEntity::find_by_id(&id).one(&state.db).await {
        Ok(Some(s)) => s,
        Ok(None) => return Err(StatusCode::NOT_FOUND),
        Err(e) => {
            tracing::error!("Failed to find source: {}", e);
            return Err(StatusCode::INTERNAL_SERVER_ERROR);
        }
    };

    let mut active_model: SourceActiveModel = source.into();
    if let Some(name) = req.name {
        active_model.name = Set(name);
    }
    if let Some(domain) = req.domain {
        active_model.domain = Set(Some(domain));
    }
    if let Some(description) = req.description {
        active_model.description = Set(Some(description));
    }
    if let Some(status) = req.status {
        active_model.status = Set(status);
    }

    match active_model.update(&state.db).await {
        Ok(model) => Ok(Json(ApiResponse {
            success: true,
            data: Some(model),
            message: Some("Source updated successfully".to_string()),
        })),
        Err(e) => {
            tracing::error!("Failed to update source: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

pub async fn delete_source(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<ApiResponse<String>>, StatusCode> {
    match SourceEntity::delete_by_id(id).exec(&state.db).await {
        Ok(_) => Ok(Json(ApiResponse {
            success: true,
            data: Some("Source deleted successfully".to_string()),
            message: None,
        })),
        Err(e) => {
            tracing::error!("Failed to delete source: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

// ===== 适配器管理 =====

#[derive(Deserialize)]
pub struct CreateAdapterRequest {
    pub id: String,
    pub name: String,
    pub script_file: String,
    pub source_id: String,
    pub topic_name: String,
}

#[derive(Serialize)]
pub struct AdapterWithSource {
    #[serde(flatten)]
    pub adapter: adapter::Model,
    pub source: Option<SourceModel>,
}

pub async fn list_adapters(
    State(state): State<AppState>,
) -> Result<Json<ApiResponse<Vec<AdapterWithSource>>>, StatusCode> {
    match adapter::Entity::find()
        .find_also_related(SourceEntity)
        .order_by_desc(adapter::Column::CreatedAt)
        .all(&state.db)
        .await
    {
        Ok(results) => {
            let adapters_with_sources: Vec<AdapterWithSource> = results
                .into_iter()
                .map(|(adapter, source)| AdapterWithSource { adapter, source })
                .collect();

            Ok(Json(ApiResponse {
                success: true,
                data: Some(adapters_with_sources),
                message: None,
            }))
        }
        Err(e) => {
            tracing::error!("Failed to list adapters: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

pub async fn get_adapter(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<ApiResponse<AdapterWithSource>>, StatusCode> {
    match adapter::Entity::find_by_id(&id)
        .find_also_related(SourceEntity)
        .one(&state.db)
        .await
    {
        Ok(Some((adapter, source))) => Ok(Json(ApiResponse {
            success: true,
            data: Some(AdapterWithSource { adapter, source }),
            message: None,
        })),
        Ok(None) => Err(StatusCode::NOT_FOUND),
        Err(e) => {
            tracing::error!("Failed to get adapter: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

pub async fn create_adapter(
    State(state): State<AppState>,
    Json(req): Json<CreateAdapterRequest>,
) -> Result<Json<ApiResponse<adapter::Model>>, StatusCode> {
    let adapter = adapter::ActiveModel {
        id: Set(req.id),
        name: Set(req.name),
        script_file: Set(req.script_file),
        source_id: Set(req.source_id),
        topic_name: Set(req.topic_name),
        status: Set("stopped".to_string()),
        total_runs: Set(0),
        successful_runs: Set(0),
        failed_runs: Set(0),
        ..Default::default()
    };

    match adapter.insert(&state.db).await {
        Ok(model) => Ok(Json(ApiResponse {
            success: true,
            data: Some(model),
            message: Some("Adapter created successfully".to_string()),
        })),
        Err(e) => {
            tracing::error!("Failed to create adapter: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

#[derive(Deserialize)]
pub struct UpdateAdapterRequest {
    pub name: Option<String>,
    pub script_file: Option<String>,
    pub topic_name: Option<String>,
}

pub async fn update_adapter(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Json(req): Json<UpdateAdapterRequest>,
) -> Result<Json<ApiResponse<adapter::Model>>, StatusCode> {
    let adapter = match adapter::Entity::find_by_id(&id).one(&state.db).await {
        Ok(Some(a)) => a,
        Ok(None) => return Err(StatusCode::NOT_FOUND),
        Err(e) => {
            tracing::error!("Failed to find adapter: {}", e);
            return Err(StatusCode::INTERNAL_SERVER_ERROR);
        }
    };

    let mut active_model: adapter::ActiveModel = adapter.into();
    if let Some(name) = req.name {
        active_model.name = Set(name);
    }
    if let Some(script_file) = req.script_file {
        active_model.script_file = Set(script_file);
    }
    if let Some(topic_name) = req.topic_name {
        active_model.topic_name = Set(topic_name);
    }

    match active_model.update(&state.db).await {
        Ok(model) => Ok(Json(ApiResponse {
            success: true,
            data: Some(model),
            message: Some("Adapter updated successfully".to_string()),
        })),
        Err(e) => {
            tracing::error!("Failed to update adapter: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

pub async fn delete_adapter(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<ApiResponse<String>>, StatusCode> {
    match adapter::Entity::delete_by_id(id).exec(&state.db).await {
        Ok(_) => Ok(Json(ApiResponse {
            success: true,
            data: Some("Adapter deleted successfully".to_string()),
            message: None,
        })),
        Err(e) => {
            tracing::error!("Failed to delete adapter: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

// ===== 适配器操作 =====

#[derive(Serialize)]
pub struct RunResult {
    pub run_id: String,
    pub status: String,
    pub message: String,
}

pub async fn run_adapter(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<ApiResponse<RunResult>>, StatusCode> {
    use crate::python_bridge::run_python_collector;
    
    // 检查适配器是否存在
    let adapter = match adapter::Entity::find_by_id(&id).one(&state.db).await {
        Ok(Some(a)) => a,
        Ok(None) => return Err(StatusCode::NOT_FOUND),
        Err(e) => {
            tracing::error!("Failed to find adapter: {}", e);
            return Err(StatusCode::INTERNAL_SERVER_ERROR);
        }
    };

    // 创建运行记录
    let run_id = Uuid::new_v4().to_string();
    let run_model = run::ActiveModel {
        id: Set(run_id.clone()),
        adapter_id: Set(id.clone()),
        started_at: Set(Utc::now().into()),
        status: Set(Some("running".to_string())),
        ..Default::default()
    };

    let run_record = match run_model.insert(&state.db).await {
        Ok(r) => r,
        Err(e) => {
            tracing::error!("Failed to create run record: {}", e);
            return Err(StatusCode::INTERNAL_SERVER_ERROR);
        }
    };

    // 异步执行采集任务
    let db = state.db.clone();
    let adapter_id = id.clone();
    let adapter_name = adapter.name.clone();
    let script_file = adapter.script_file.clone();
    let topic_name = adapter.topic_name.clone();
    
    tokio::spawn(async move {
        tracing::info!("🚀 Starting collection for adapter: {}", adapter_id);
        
        let result = run_python_collector(&script_file, Some(100)).await;
        
        match result {
            Ok(records) => {
                tracing::info!("✅ Collected {} records from {}", records.len(), adapter_id);
                
                // 保存采集记录到数据库
                let mut new_records = 0;
                let mut duplicate_records = 0;
                let mut failed_records = 0;
                
                for raw_record in records {
                    // 创建采集记录
                    let record_id = Uuid::new_v4().to_string();
                    
                    // 解析日期
                    let business_date = match chrono::NaiveDate::parse_from_str(&raw_record.business_date, "%Y-%m-%d") {
                        Ok(date) => date,
                        Err(_) => {
                            tracing::warn!("Invalid date format: {}", raw_record.business_date);
                            failed_records += 1;
                            continue;
                        }
                    };
                    
                    let record_model = record::ActiveModel {
                        id: Set(record_id),
                        adapter_id: Set(adapter_id.clone()),
                        business_date: Set(business_date),
                        value: Set(Some(rust_decimal::Decimal::from_f64_retain(raw_record.value).unwrap_or_default())),
                        unit: Set(Some(raw_record.unit)),
                        topic_name: Set(Some(topic_name.clone())),
                        source_url: Set(Some(raw_record.source_url)),
                        source_html_path: Set(None),
                        quality_grade: Set(None),
                        quality_score: Set(None),
                        collected_at: Set(Utc::now().into()),
                        ..Default::default()
                    };
                    
                    match record_model.insert(&db).await {
                        Ok(_) => new_records += 1,
                        Err(e) => {
                            if e.to_string().contains("duplicate") || e.to_string().contains("unique") {
                                duplicate_records += 1;
                            } else {
                                tracing::error!("Failed to insert record: {}", e);
                                failed_records += 1;
                            }
                        }
                    }
                }
                
                // 更新运行记录
                let mut run_update: run::ActiveModel = run_record.into();
                run_update.status = Set(Some("success".to_string()));
                run_update.completed_at = Set(Some(Utc::now().into()));
                run_update.new_records = Set(Some(new_records));
                run_update.duplicate_records = Set(Some(duplicate_records));
                run_update.failed_records = Set(Some(failed_records));
                
                if let Err(e) = run_update.update(&db).await {
                    tracing::error!("Failed to update run record: {}", e);
                }
                
                // 更新适配器统计
                if let Ok(Some(adapter)) = adapter::Entity::find_by_id(&adapter_id).one(&db).await {
                    let mut adapter_update: adapter::ActiveModel = adapter.into();
                    adapter_update.last_run_at = Set(Some(Utc::now().into()));
                    adapter_update.total_runs = Set(adapter_update.total_runs.unwrap() + 1);
                    adapter_update.successful_runs = Set(adapter_update.successful_runs.unwrap() + 1);
                    
                    if let Err(e) = adapter_update.update(&db).await {
                        tracing::error!("Failed to update adapter stats: {}", e);
                    }
                }
                
                tracing::info!("📊 Run complete: {} new, {} duplicate, {} failed", 
                    new_records, duplicate_records, failed_records);
            }
            Err(e) => {
                tracing::error!("❌ Collection failed for {}: {}", adapter_id, e);
                
                // 更新运行记录为失败
                let mut run_update: run::ActiveModel = run_record.into();
                run_update.status = Set(Some("failed".to_string()));
                run_update.completed_at = Set(Some(Utc::now().into()));
                run_update.error_message = Set(Some(e.to_string()));
                
                if let Err(e) = run_update.update(&db).await {
                    tracing::error!("Failed to update run record: {}", e);
                }
                
                // 更新适配器统计
                if let Ok(Some(adapter)) = adapter::Entity::find_by_id(&adapter_id).one(&db).await {
                    let mut adapter_update: adapter::ActiveModel = adapter.into();
                    adapter_update.last_run_at = Set(Some(Utc::now().into()));
                    adapter_update.total_runs = Set(adapter_update.total_runs.unwrap() + 1);
                    adapter_update.failed_runs = Set(adapter_update.failed_runs.unwrap() + 1);
                    adapter_update.last_error = Set(Some(e));
                    
                    if let Err(e) = adapter_update.update(&db).await {
                        tracing::error!("Failed to update adapter stats: {}", e);
                    }
                }
            }
        }
    });

    Ok(Json(ApiResponse {
        success: true,
        data: Some(RunResult {
            run_id,
            status: "running".to_string(),
            message: format!("Collection started for adapter: {}", adapter_name),
        }),
        message: None,
    }))
}

pub async fn start_adapter(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<ApiResponse<adapter::Model>>, StatusCode> {
    let adapter = match adapter::Entity::find_by_id(&id).one(&state.db).await {
        Ok(Some(a)) => a,
        Ok(None) => return Err(StatusCode::NOT_FOUND),
        Err(e) => {
            tracing::error!("Failed to find adapter: {}", e);
            return Err(StatusCode::INTERNAL_SERVER_ERROR);
        }
    };

    let mut active_model: adapter::ActiveModel = adapter.into();
    active_model.status = Set("running".to_string());

    match active_model.update(&state.db).await {
        Ok(model) => Ok(Json(ApiResponse {
            success: true,
            data: Some(model),
            message: Some("Adapter started".to_string()),
        })),
        Err(e) => {
            tracing::error!("Failed to start adapter: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

pub async fn stop_adapter(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<ApiResponse<adapter::Model>>, StatusCode> {
    let adapter = match adapter::Entity::find_by_id(&id).one(&state.db).await {
        Ok(Some(a)) => a,
        Ok(None) => return Err(StatusCode::NOT_FOUND),
        Err(e) => {
            tracing::error!("Failed to find adapter: {}", e);
            return Err(StatusCode::INTERNAL_SERVER_ERROR);
        }
    };

    let mut active_model: adapter::ActiveModel = adapter.into();
    active_model.status = Set("stopped".to_string());

    match active_model.update(&state.db).await {
        Ok(model) => Ok(Json(ApiResponse {
            success: true,
            data: Some(model),
            message: Some("Adapter stopped".to_string()),
        })),
        Err(e) => {
            tracing::error!("Failed to stop adapter: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

// ===== 运行历史 =====

#[derive(Deserialize)]
pub struct RunsQuery {
    pub limit: Option<u64>,
}

pub async fn get_adapter_runs(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Query(query): Query<RunsQuery>,
) -> Result<Json<ApiResponse<Vec<run::Model>>>, StatusCode> {
    let limit = query.limit.unwrap_or(20);

    match run::Entity::find()
        .filter(run::Column::AdapterId.eq(id))
        .order_by_desc(run::Column::StartedAt)
        .limit(limit)
        .all(&state.db)
        .await
    {
        Ok(runs) => Ok(Json(ApiResponse {
            success: true,
            data: Some(runs),
            message: None,
        })),
        Err(e) => {
            tracing::error!("Failed to get adapter runs: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

// ===== 采集记录 =====

#[derive(Deserialize)]
pub struct RecordsQuery {
    pub limit: Option<u64>,
}

pub async fn get_adapter_records(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Query(query): Query<RecordsQuery>,
) -> Result<Json<ApiResponse<Vec<record::Model>>>, StatusCode> {
    let limit = query.limit.unwrap_or(50);

    match record::Entity::find()
        .filter(record::Column::AdapterId.eq(id))
        .order_by_desc(record::Column::BusinessDate)
        .limit(limit)
        .all(&state.db)
        .await
    {
        Ok(records) => Ok(Json(ApiResponse {
            success: true,
            data: Some(records),
            message: None,
        })),
        Err(e) => {
            tracing::error!("Failed to get adapter records: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

// ===== 数据主题 =====

#[derive(Serialize)]
pub struct TopicInfo {
    pub name: String,
    pub adapter_count: u64,
    pub record_count: u64,
    pub latest_date: Option<String>,
}

pub async fn list_topics(
    State(state): State<AppState>,
) -> Result<Json<ApiResponse<Vec<TopicInfo>>>, StatusCode> {
    // 获取所有独特的主题名称
    match adapter::Entity::find().all(&state.db).await {
        Ok(adapters) => {
            use std::collections::HashMap;
            let mut topics: HashMap<String, TopicInfo> = HashMap::new();

            for adapter in adapters {
                let topic_name = adapter.topic_name.clone();
                let entry = topics.entry(topic_name.clone()).or_insert(TopicInfo {
                    name: topic_name,
                    adapter_count: 0,
                    record_count: 0,
                    latest_date: None,
                });
                entry.adapter_count += 1;
            }

            let mut result: Vec<TopicInfo> = topics.into_values().collect();
            result.sort_by(|a, b| a.name.cmp(&b.name));

            Ok(Json(ApiResponse {
                success: true,
                data: Some(result),
                message: None,
            }))
        }
        Err(e) => {
            tracing::error!("Failed to list topics: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

#[derive(Serialize)]
pub struct TopicDetail {
    pub name: String,
    pub adapters: Vec<AdapterWithSource>,
    pub record_count: u64,
}

pub async fn get_topic(
    State(state): State<AppState>,
    Path(name): Path<String>,
) -> Result<Json<ApiResponse<TopicDetail>>, StatusCode> {
    match adapter::Entity::find()
        .filter(adapter::Column::TopicName.eq(&name))
        .find_also_related(SourceEntity)
        .all(&state.db)
        .await
    {
        Ok(results) => {
            let adapters: Vec<AdapterWithSource> = results
                .into_iter()
                .map(|(adapter, source)| AdapterWithSource { adapter, source })
                .collect();

            let record_count = record::Entity::find()
                .filter(record::Column::TopicName.eq(&name))
                .count(&state.db)
                .await
                .unwrap_or(0);

            Ok(Json(ApiResponse {
                success: true,
                data: Some(TopicDetail {
                    name,
                    adapters,
                    record_count,
                }),
                message: None,
            }))
        }
        Err(e) => {
            tracing::error!("Failed to get topic: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

#[derive(Deserialize)]
pub struct TopicRecordsQuery {
    pub start_date: Option<String>,
    pub end_date: Option<String>,
    pub limit: Option<u64>,
}

pub async fn get_topic_records(
    State(state): State<AppState>,
    Path(name): Path<String>,
    Query(query): Query<TopicRecordsQuery>,
) -> Result<Json<ApiResponse<Vec<record::Model>>>, StatusCode> {
    let limit = query.limit.unwrap_or(100);

    let query_builder = record::Entity::find()
        .filter(record::Column::TopicName.eq(name));

    // TODO: 添加日期过滤

    match query_builder
        .order_by_desc(record::Column::BusinessDate)
        .limit(limit)
        .all(&state.db)
        .await
    {
        Ok(records) => Ok(Json(ApiResponse {
            success: true,
            data: Some(records),
            message: None,
        })),
        Err(e) => {
            tracing::error!("Failed to get topic records: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}

// ===== 通用记录查询 =====

#[derive(Deserialize)]
pub struct RecordsQueryParams {
    pub adapter_id: Option<String>,
    pub topic: Option<String>,
    pub start_date: Option<String>,
    pub end_date: Option<String>,
    pub quality: Option<String>,
    pub limit: Option<u64>,
}

pub async fn query_records(
    State(state): State<AppState>,
    Query(params): Query<RecordsQueryParams>,
) -> Result<Json<ApiResponse<Vec<record::Model>>>, StatusCode> {
    let limit = params.limit.unwrap_or(100);

    let mut query_builder = record::Entity::find();

    if let Some(adapter_id) = params.adapter_id {
        query_builder = query_builder.filter(record::Column::AdapterId.eq(adapter_id));
    }

    if let Some(topic) = params.topic {
        query_builder = query_builder.filter(record::Column::TopicName.eq(topic));
    }

    if let Some(quality) = params.quality {
        query_builder = query_builder.filter(record::Column::QualityGrade.eq(quality));
    }

    match query_builder
        .order_by_desc(record::Column::BusinessDate)
        .limit(limit)
        .all(&state.db)
        .await
    {
        Ok(records) => Ok(Json(ApiResponse {
            success: true,
            data: Some(records),
            message: None,
        })),
        Err(e) => {
            tracing::error!("Failed to query records: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}
