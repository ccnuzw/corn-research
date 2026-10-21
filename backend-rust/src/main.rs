//! Corn Backend - Rust Web服务
//!
//! 提供REST API和WebSocket服务

use axum::{
    Router,
    routing::{get, post},
    Json,
    response::IntoResponse,
    extract::{State, Path, Query},
};
use serde::{Serialize, Deserialize};
use tower_http::cors::CorsLayer;
use std::net::SocketAddr;
use std::sync::Arc;

mod handlers;
mod python_bridge;
mod errors;
mod scheduler;
mod notification;
mod models;
mod db;
mod standardization;
mod lineage_handlers;
mod collection_handlers;

use scheduler::JobManager;
use notification::NotificationService;
use standardization::{StandardizationService, StandardEntity};
use lineage_handlers::{get_data_lineage, trigger_standardization, trigger_auto_promotion};

#[derive(Serialize)]
struct ApiResponse<T> {
    success: bool,
    data: Option<T>,
    message: Option<String>,
}

/// 应用状态
#[derive(Clone)]
struct AppState {
    notification_service: NotificationService,
    job_manager: Arc<tokio::sync::Mutex<JobManager>>,
    db: sea_orm::DatabaseConnection,
    standardization_service: Arc<StandardizationService>,
}

#[tokio::main]
async fn main() {
    // 加载环境变量
    dotenvy::dotenv().ok();
    
    // 初始化日志（支持RUST_LOG环境变量）
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info"))
        )
        .init();

    tracing::info!("🌽 Corn Backend V2 starting...");

    // 初始化数据库连接
    let database_url = std::env::var("DATABASE_URL")
        .unwrap_or_else(|_| "postgresql://corn_user:corn_password_2026@localhost:15432/corn_research".to_string());
    
    let db = db::connect(&database_url)
        .await
        .expect("Failed to connect to database");
    
    tracing::info!("✅ Database connected");

    // 初始化通知服务
    let redis_url = std::env::var("REDIS_URL")
        .unwrap_or_else(|_| "redis://localhost:16380".to_string());
    
    let notification_service = NotificationService::new(&redis_url)
        .await
        .expect("Failed to initialize notification service");
    
    // 初始化任务调度器
    let job_manager = JobManager::new()
        .await
        .expect("Failed to initialize job manager");
    
    job_manager.start()
        .await
        .expect("Failed to start job scheduler");
    
    // 添加每日采集任务（每天8:00）
    job_manager
        .add_daily_collection_job(vec![
            "boyar".to_string(),
            "sina".to_string(),
        ])
        .await
        .expect("Failed to add daily collection job");
    
    // 初始化标准化服务
    let standardization_service = StandardizationService::new(db.clone());
    
    let app_state = AppState {
        notification_service,
        job_manager: Arc::new(tokio::sync::Mutex::new(job_manager)),
        db,
        standardization_service: Arc::new(standardization_service),
    };

    // 构建路由
    let app = Router::new()
        // 健康检查
        .route("/health", get(health_check))
        
        // 采集管理API - 数据源
        .route("/api/sources", get(collection_handlers::list_sources))
        .route("/api/sources", post(collection_handlers::create_source))
        .route("/api/sources/:id", get(collection_handlers::get_source))
        .route("/api/sources/:id", axum::routing::put(collection_handlers::update_source))
        .route("/api/sources/:id", axum::routing::delete(collection_handlers::delete_source))
        
        // 采集管理API - 适配器
        .route("/api/adapters", get(collection_handlers::list_adapters))
        .route("/api/adapters", post(collection_handlers::create_adapter))
        .route("/api/adapters/:id", get(collection_handlers::get_adapter))
        .route("/api/adapters/:id", axum::routing::put(collection_handlers::update_adapter))
        .route("/api/adapters/:id", axum::routing::delete(collection_handlers::delete_adapter))
        .route("/api/adapters/:id/run", post(collection_handlers::run_adapter))
        .route("/api/adapters/:id/start", post(collection_handlers::start_adapter))
        .route("/api/adapters/:id/stop", post(collection_handlers::stop_adapter))
        .route("/api/adapters/:id/runs", get(collection_handlers::get_adapter_runs))
        .route("/api/adapters/:id/records", get(collection_handlers::get_adapter_records))
        
        // 采集管理API - 数据主题
        .route("/api/topics", get(collection_handlers::list_topics))
        .route("/api/topics/:name", get(collection_handlers::get_topic))
        .route("/api/topics/:name/records", get(collection_handlers::get_topic_records))
        
        // 采集管理API - 记录查询
        .route("/api/records", get(collection_handlers::query_records))
        
        // 采集器API (保留原有)
        .route("/api/collectors", get(handlers::list_collectors))
        .route("/api/collectors/:id/run", post(handlers::run_collector))
        .route("/api/collectors/:id/history", get(handlers::get_collector_history))
        .route("/api/collectors/:id/status", get(handlers::get_collector_status))
        
        // 数据API
        .route("/api/data/latest", get(handlers::get_latest_data))
        .route("/api/data/stats", get(handlers::get_stats))
        .route("/api/data/trend", get(handlers::get_trend_data))
        .route("/api/data/indicators", get(handlers::get_indicators))
        
        // 数据质量API
        .route("/api/quality/scores", get(handlers::get_quality_scores))
        .route("/api/quality/distribution", get(handlers::get_quality_distribution))
        .route("/api/quality/issues", get(handlers::get_quality_issues))
        
        // 数据血统API
        .route("/api/data/:id/lineage", get(get_data_lineage))
        .route("/api/data/standardize", post(trigger_standardization))
        .route("/api/data/auto-promote", post(trigger_auto_promotion))
        
        // 通知API
        .route("/api/notifications", get(get_notifications))
        .route("/api/notifications/mark-read", post(mark_notification_read))
        
        // 定时任务API
        .route("/api/scheduler/jobs", get(list_jobs))
        .route("/api/scheduler/jobs", post(create_job))
        .route("/api/scheduler/jobs/:id", post(trigger_job))
        .route("/api/scheduler/jobs/:id", axum::routing::put(update_job))
        .route("/api/scheduler/jobs/:id", axum::routing::delete(delete_job))
        .route("/api/scheduler/jobs/:id/enable", axum::routing::put(toggle_job))
        
        // WebSocket（TODO: 实现）
        // .route("/ws/notifications", get(ws_handler))
        
        // CORS
        .layer(CorsLayer::permissive())
        .with_state(app_state);

    // 启动服务
    let port = std::env::var("SERVER_PORT")
        .unwrap_or_else(|_| "8000".to_string())
        .parse::<u16>()
        .unwrap_or(8000);
    
    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    tracing::info!("🚀 Corn Backend listening on http://{}", addr);
    
    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn health_check() -> impl IntoResponse {
    Json(ApiResponse {
        success: true,
        data: Some("Corn Backend V2 is running"),
        message: None,
    })
}

// ===== 通知API =====

#[derive(Deserialize)]
struct NotificationQuery {
    limit: Option<usize>,
}

async fn get_notifications(
    State(state): State<AppState>,
    Query(query): Query<NotificationQuery>,
) -> impl IntoResponse {
    let limit = query.limit.unwrap_or(50);
    
    match state.notification_service.get_history(limit).await {
        Ok(notifications) => Json(ApiResponse {
            success: true,
            data: Some(notifications),
            message: None,
        }),
        Err(e) => {
            tracing::error!("Failed to get notifications: {}", e);
            Json(ApiResponse {
                success: false,
                data: None,
                message: Some(e.to_string()),
            })
        }
    }
}

#[derive(Deserialize)]
struct MarkReadRequest {
    notification_id: String,
}

async fn mark_notification_read(
    State(state): State<AppState>,
    Json(req): Json<MarkReadRequest>,
) -> impl IntoResponse {
    match state.notification_service.mark_as_read(&req.notification_id).await {
        Ok(_) => Json(ApiResponse {
            success: true,
            data: Some("Notification marked as read"),
            message: None,
        }),
        Err(e) => {
            tracing::error!("Failed to mark notification as read: {}", e);
            Json(ApiResponse {
                success: false,
                data: None,
                message: Some(e.to_string()),
            })
        }
    }
}

// ===== 定时任务API =====

async fn list_jobs(
    State(state): State<AppState>,
) -> impl IntoResponse {
    let jobs = state.job_manager.lock().await.list_jobs().await;
    
    Json(ApiResponse {
        success: true,
        data: Some(jobs),
        message: None,
    })
}

#[derive(Deserialize)]
struct CreateJobRequest {
    name: String,
    collector_id: String,
    cron_expression: String,
    description: Option<String>,
    enabled: Option<bool>,
}

async fn create_job(
    State(state): State<AppState>,
    Json(req): Json<CreateJobRequest>,
) -> impl IntoResponse {
    let enabled = req.enabled.unwrap_or(true);
    
    match state.job_manager.lock().await.add_collector_job(
        req.name,
        req.collector_id,
        &req.cron_expression,
        req.description,
    ).await {
        Ok(job_id) => Json(ApiResponse {
            success: true,
            data: Some(serde_json::json!({
                "job_id": job_id.to_string(),
            })),
            message: Some("Job created successfully".to_string()),
        }),
        Err(e) => Json(ApiResponse {
            success: false,
            data: None,
            message: Some(format!("Failed to create job: {}", e)),
        })
    }
}

#[derive(Deserialize)]
struct UpdateJobRequest {
    name: Option<String>,
    cron_expression: Option<String>,
    description: Option<String>,
}

async fn update_job(
    State(state): State<AppState>,
    Path(job_id): Path<String>,
    Json(req): Json<UpdateJobRequest>,
) -> impl IntoResponse {
    // 目前tokio-cron-scheduler不支持直接更新任务
    // 需要删除旧任务并创建新任务
    Json(ApiResponse::<()> {
        success: false,
        data: None,
        message: Some("Job update requires recreation (not yet implemented)".to_string()),
    })
}

async fn delete_job(
    State(state): State<AppState>,
    Path(job_id): Path<String>,
) -> impl IntoResponse {
    match uuid::Uuid::parse_str(&job_id) {
        Ok(uuid) => {
            match state.job_manager.lock().await.remove_job(uuid).await {
                Ok(_) => Json(ApiResponse {
                    success: true,
                    data: Some("Job deleted"),
                    message: None,
                }),
                Err(e) => Json(ApiResponse {
                    success: false,
                    data: None,
                    message: Some(e.to_string()),
                })
            }
        }
        Err(e) => Json(ApiResponse {
            success: false,
            data: None,
            message: Some(format!("Invalid job ID: {}", e)),
        })
    }
}

#[derive(Deserialize)]
struct ToggleJobRequest {
    enabled: bool,
}

async fn toggle_job(
    State(state): State<AppState>,
    Path(job_id): Path<String>,
    Json(req): Json<ToggleJobRequest>,
) -> impl IntoResponse {
    match uuid::Uuid::parse_str(&job_id) {
        Ok(uuid) => {
            match state.job_manager.lock().await.toggle_job(uuid, req.enabled).await {
                Ok(_) => Json(ApiResponse {
                    success: true,
                    data: Some("Job toggled"),
                    message: None,
                }),
                Err(e) => Json(ApiResponse {
                    success: false,
                    data: None,
                    message: Some(e.to_string()),
                })
            }
        }
        Err(e) => Json(ApiResponse {
            success: false,
            data: None,
            message: Some(format!("Invalid job ID: {}", e)),
        })
    }
}

async fn trigger_job(
    State(state): State<AppState>,
    Path(job_id): Path<String>,
) -> impl IntoResponse {
    match uuid::Uuid::parse_str(&job_id) {
        Ok(uuid) => {
            match state.job_manager.lock().await.trigger_job(uuid).await {
                Ok(_) => Json(ApiResponse {
                    success: true,
                    data: Some("Job triggered"),
                    message: None,
                }),
                Err(e) => Json(ApiResponse {
                    success: false,
                    data: None,
                    message: Some(e.to_string()),
                })
            }
        }
        Err(e) => Json(ApiResponse {
            success: false,
            data: None,
            message: Some(format!("Invalid job ID: {}", e)),
        })
    }
}
