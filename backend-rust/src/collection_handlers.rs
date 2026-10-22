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
use crate::db::entities::{Entity as RawRecordEntity, Column as RawRecordColumn};

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
    let adapter = adapter::Entity::find_by_id(&id).one(&state.db).await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
        .ok_or(StatusCode::NOT_FOUND)?;
    let history = crate::collection_execution::start_run(&state.db, &id).await
        .map_err(|e| {
            tracing::error!("Failed to create run: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;
    let run_id = history.id.clone();
    let name = adapter.name.clone();
    let db = state.db.clone();
    tokio::spawn(async move {
        if let Err(e) = crate::collection_execution::execute_run(db, adapter, history, 100, true).await {
            tracing::error!("Collection failed: {}", e);
        }
    });
    Ok(Json(ApiResponse {
        success: true,
        data: Some(RunResult {
            run_id, status: "running".to_string(),
            message: format!("Collection started for adapter: {}", name),
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
    pub offset: Option<u64>,
}

pub async fn get_adapter_runs(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Query(query): Query<RunsQuery>,
) -> Result<Json<ApiResponse<Vec<crate::collection_execution::CollectionRun>>>, StatusCode> {
    let limit = query.limit.unwrap_or(20);
    if !(1..=100).contains(&limit) {
        return Err(StatusCode::BAD_REQUEST);
    }
    if adapter::Entity::find_by_id(&id).one(&state.db).await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?.is_none() {
        return Err(StatusCode::NOT_FOUND);
    }

    match run::Entity::find()
        .filter(run::Column::AdapterId.eq(id))
        .order_by_desc(run::Column::StartedAt)
        .order_by_desc(run::Column::Id)
        .offset(query.offset.unwrap_or(0))
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

    // Query raw_collection_records table instead
    let mut query_builder = RawRecordEntity::find();

    if let Some(adapter_id) = params.adapter_id {
        query_builder = query_builder.filter(RawRecordColumn::CollectorId.eq(adapter_id));
    }

    if let Some(topic) = params.topic {
        query_builder = query_builder.filter(RawRecordColumn::IndicatorName.eq(topic));
    }

    match query_builder
        .order_by_desc(RawRecordColumn::BusinessDate)
        .order_by_desc(RawRecordColumn::CollectedAt)
        .limit(limit)
        .all(&state.db)
        .await
    {
        Ok(raw_records) => {
            tracing::info!("✅ Found {} records", raw_records.len());
            // Map raw records to the record format expected by frontend
            let records: Vec<record::Model> = raw_records
                .into_iter()
                .map(|raw| record::Model {
                    id: raw.id.to_string(),
                    adapter_id: raw.collector_id,
                    business_date: raw.business_date,
                    value: Some(raw.value),
                    unit: Some(raw.unit),
                    topic_name: Some(raw.indicator_name),
                    record_key: String::new(),
                    indicator: None,
                    region: raw.region,
                    metadata: None,
                    source_url: Some(raw.source_url),
                    source_html_path: None,
                    quality_grade: None,
                    quality_score: None,
                    collected_at: raw.collected_at,
                    created_at: raw.created_at,
                })
                .collect();

            Ok(Json(ApiResponse {
                success: true,
                data: Some(records),
                message: None,
            }))
        }
        Err(e) => {
            tracing::error!("Failed to query records: {}", e);
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}
