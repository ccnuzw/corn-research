# 玉米研究系统V2 - 技术栈完善方案

**目标**: 在引入SeaORM基础上，完善整个技术栈，打造生产就绪的企业级系统

---

## 📊 当前技术栈现状

### ✅ 已有组件
```
前端:
- Next.js 14
- TypeScript
- Shadcn/ui
- TailwindCSS

后端:
- Rust 1.85
- Axum 0.7
- Tokio 1.35
- PyO3 0.20
- SQLx 0.7 (待替换为SeaORM)

数据库:
- PostgreSQL 16
- TimescaleDB
- Redis 7

部署:
- Docker + Docker Compose
- 4个容器 (frontend, backend, postgres, redis)

Python采集器:
- requests
- beautifulsoup4
- lxml
```

---

## 🔍 缺失的关键组件

### 1. ⚠️ 日志系统（高优先级）

#### 当前问题
```
✗ 没有统一日志格式
✗ 没有日志级别控制
✗ 没有日志持久化
✗ 调试困难
```

#### 推荐方案
```toml
# backend-rust/Cargo.toml
[dependencies]
# 日志框架
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json"] }
tracing-appender = "0.2"

# 结构化日志
serde_json = "1.0"
```

#### 实现示例
```rust
// main.rs
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

fn init_logging() {
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info,corn_backend=debug".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .init();
}

// 使用
#[instrument]
async fn collect_data(collector_id: &str) -> Result<Vec<Record>> {
    info!("开始采集: {}", collector_id);
    // ...
    info!(records = records.len(), "采集完成");
    Ok(records)
}
```

---

### 2. ⚠️ 错误处理（高优先级）

#### 当前问题
```
✗ 错误类型不统一
✗ 缺少自定义错误
✗ 错误信息不友好
✗ 难以追踪错误链
```

#### 推荐方案
```toml
[dependencies]
thiserror = "1.0"   # 自定义错误
anyhow = "1.0"      # 错误传播
```

#### 实现示例
```rust
// errors.rs
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("数据库错误: {0}")]
    Database(#[from] sea_orm::DbErr),
    
    #[error("Python采集器错误: {0}")]
    Collector(String),
    
    #[error("验证错误: {0}")]
    Validation(String),
    
    #[error("未找到: {0}")]
    NotFound(String),
}

// Axum错误响应
impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, message) = match self {
            AppError::NotFound(msg) => (StatusCode::NOT_FOUND, msg),
            AppError::Validation(msg) => (StatusCode::BAD_REQUEST, msg),
            _ => (StatusCode::INTERNAL_SERVER_ERROR, self.to_string()),
        };
        
        (status, Json(json!({ "error": message }))).into_response()
    }
}
```

---

### 3. ⚠️ 配置管理（高优先级）

#### 当前问题
```
✗ 配置硬编码
✗ 没有环境区分
✗ 密钥明文存储
✗ 难以部署
```

#### 推荐方案
```toml
[dependencies]
config = "0.14"
dotenvy = "0.15"
serde = { version = "1.0", features = ["derive"] }
```

#### 实现示例
```rust
// config.rs
use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct Config {
    pub database: DatabaseConfig,
    pub server: ServerConfig,
    pub collectors: CollectorConfig,
}

#[derive(Debug, Deserialize)]
pub struct DatabaseConfig {
    pub url: String,
    pub max_connections: u32,
}

#[derive(Debug, Deserialize)]
pub struct ServerConfig {
    pub host: String,
    pub port: u16,
}

impl Config {
    pub fn load() -> Result<Self> {
        let config = config::Config::builder()
            .add_source(config::File::with_name("config/default"))
            .add_source(config::File::with_name(&format!(
                "config/{}",
                std::env::var("ENV").unwrap_or_else(|_| "development".into())
            )).required(false))
            .add_source(config::Environment::with_prefix("CORN"))
            .build()?;
        
        config.try_deserialize()
    }
}
```

```yaml
# config/default.yaml
database:
  url: "postgresql://corn_user:***@localhost:15432/corn_research"
  max_connections: 5

server:
  host: "0.0.0.0"
  port: 18000

collectors:
  timeout_seconds: 30
  retry_attempts: 3
```

---

### 4. ⚠️ API文档（中优先级）

#### 当前问题
```
✗ 没有API文档
✗ 前端不知道接口规范
✗ 调试困难
```

#### 推荐方案
```toml
[dependencies]
utoipa = "4.0"              # OpenAPI生成
utoipa-swagger-ui = "4.0"   # Swagger UI
```

#### 实现示例
```rust
use utoipa::{OpenApi, ToSchema};

#[derive(OpenApi)]
#[openapi(
    paths(
        get_latest_data,
        run_collector,
    ),
    components(
        schemas(MarketDataDto, CollectionResult)
    ),
    tags(
        (name = "data", description = "数据查询接口"),
        (name = "collectors", description = "采集器管理接口")
    )
)]
struct ApiDoc;

// 在main.rs中挂载
let app = Router::new()
    .merge(SwaggerUi::new("/swagger-ui")
        .url("/api-docs/openapi.json", ApiDoc::openapi()));
```

访问: `http://localhost:18000/swagger-ui/`

---

### 5. ⚠️ 数据验证（中优先级）

#### 当前问题
```
✗ 没有输入验证
✗ 脏数据可能写入数据库
✗ 安全风险
```

#### 推荐方案
```toml
[dependencies]
validator = { version = "0.16", features = ["derive"] }
```

#### 实现示例
```rust
use validator::Validate;

#[derive(Debug, Validate, Deserialize)]
pub struct CollectorRequest {
    #[validate(length(min = 1, max = 100))]
    pub collector_id: String,
    
    #[validate(range(min = 1, max = 365))]
    pub days: Option<u32>,
}

async fn run_collector(
    Json(req): Json<CollectorRequest>,
) -> Result<Json<CollectionResult>, AppError> {
    req.validate()?;  // 自动验证
    // ...
}
```

---

### 6. ⚠️ 监控和指标（中优先级）

#### 当前问题
```
✗ 没有性能监控
✗ 不知道系统健康度
✗ 问题发现太晚
```

#### 推荐方案
```toml
[dependencies]
metrics = "0.21"
metrics-exporter-prometheus = "0.13"
```

#### 实现示例
```rust
use metrics::{counter, histogram};

async fn collect_data(collector_id: &str) -> Result<Vec<Record>> {
    let start = Instant::now();
    
    let result = do_collect(collector_id).await;
    
    histogram!("collection_duration_seconds", start.elapsed().as_secs_f64());
    
    if result.is_ok() {
        counter!("collection_success_total", 1);
    } else {
        counter!("collection_error_total", 1);
    }
    
    result
}
```

访问Prometheus指标: `http://localhost:18000/metrics`

---

### 7. ⚠️ 定时任务（中优先级）

#### 当前问题
```
✗ 手动运行采集
✗ 没有定时调度
✗ 没有任务队列
```

#### 推荐方案
```toml
[dependencies]
tokio-cron-scheduler = "0.9"
```

#### 实现示例
```rust
use tokio_cron_scheduler::{JobScheduler, Job};

async fn setup_scheduler(orchestrator: Arc<CollectionOrchestrator>) {
    let sched = JobScheduler::new().await.unwrap();
    
    // 每天早上8点采集
    sched.add(
        Job::new_async("0 0 8 * * *", move |_uuid, _l| {
            Box::pin(async move {
                info!("开始定时采集");
                orchestrator.run_all_collectors().await.unwrap();
            })
        }).unwrap()
    ).await.unwrap();
    
    sched.start().await.unwrap();
}
```

---

### 8. ⚠️ 缓存层（低优先级）

#### 当前问题
```
✗ 重复查询数据库
✗ 响应慢
```

#### 推荐方案
```toml
[dependencies]
redis = { version = "0.24", features = ["tokio-comp", "connection-manager"] }
```

#### 实现示例
```rust
use redis::AsyncCommands;

async fn get_latest_data_cached(
    indicator: &str,
    cache: &ConnectionManager,
    db: &DatabaseConnection,
) -> Result<Vec<MarketData>> {
    let cache_key = format!("latest:{}:30", indicator);
    
    // 尝试从缓存获取
    if let Ok(cached) = cache.get::<_, String>(&cache_key).await {
        if let Ok(data) = serde_json::from_str(&cached) {
            return Ok(data);
        }
    }
    
    // 从数据库获取
    let data = db.get_latest(indicator, 30).await?;
    
    // 写入缓存（5分钟过期）
    let _: () = cache.set_ex(
        &cache_key,
        serde_json::to_string(&data)?,
        300
    ).await?;
    
    Ok(data)
}
```

---

### 9. ⚠️ 测试框架（中优先级）

#### 当前问题
```
✗ 没有单元测试
✗ 没有集成测试
✗ 代码质量无保障
```

#### 推荐方案
```toml
[dev-dependencies]
tokio-test = "0.4"
mockall = "0.12"
fake = "2.9"
```

#### 实现示例
```rust
#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_save_raw_records() {
        let db = setup_test_db().await;
        let repo = PostgresRepository::new(db);
        
        let records = vec![
            create_test_record("山东到车", 1000.0),
        ];
        
        let saved = repo.save_raw_records(&records).await.unwrap();
        
        assert_eq!(saved, 1);
    }
}
```

---

### 10. ⚠️ 数据库迁移（高优先级）

#### 当前问题
```
✗ 手动执行SQL
✗ 版本管理混乱
✗ 团队协作困难
```

#### 推荐方案（SeaORM自带）
```bash
# 安装CLI
cargo install sea-orm-cli

# 创建迁移
sea-orm-cli migrate generate create_raw_table

# 执行迁移
sea-orm-cli migrate up

# 回滚
sea-orm-cli migrate down
```

---

## 📦 完整的依赖清单

### backend-rust/Cargo.toml
```toml
[package]
name = "corn-backend"
version = "0.1.0"
edition = "2021"

[dependencies]
# Web框架
axum = { version = "0.7", features = ["macros"] }
tokio = { version = "1", features = ["full"] }
tower = "0.4"
tower-http = { version = "0.5", features = ["cors", "fs", "trace"] }

# ORM (新增)
sea-orm = { version = "0.12", features = [
    "sqlx-postgres",
    "runtime-tokio-native-tls",
    "macros",
    "with-chrono",
    "with-uuid"
]}

# 序列化
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

# Python集成
pyo3 = { version = "0.20", features = ["auto-initialize"] }

# 日志 (新增)
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json"] }
tracing-appender = "0.2"

# 错误处理 (新增)
thiserror = "1.0"
anyhow = "1.0"

# 配置管理 (新增)
config = "0.14"
dotenvy = "0.15"

# API文档 (新增)
utoipa = { version = "4.0", features = ["axum_extras"] }
utoipa-swagger-ui = { version = "4.0", features = ["axum"] }

# 数据验证 (新增)
validator = { version = "0.16", features = ["derive"] }

# 监控 (新增)
metrics = "0.21"
metrics-exporter-prometheus = "0.13"

# 定时任务 (新增)
tokio-cron-scheduler = "0.9"

# 缓存
redis = { version = "0.24", features = ["tokio-comp", "connection-manager"] }

# 工具
chrono = { version = "0.4", features = ["serde"] }
uuid = { version = "1.6", features = ["v4", "serde"] }

# 项目内部依赖
corn-domain = { path = "../core-rust/corn-domain" }
corn-infrastructure = { path = "../core-rust/corn-infrastructure" }

[dev-dependencies]
tokio-test = "0.4"
mockall = "0.12"
fake = "2.9"
```

---

## 🗂️ 项目结构完善

```
/Users/apple/CornV2/
├── backend-rust/
│   ├── src/
│   │   ├── main.rs
│   │   ├── config.rs          # 新增：配置管理
│   │   ├── errors.rs          # 新增：错误类型
│   │   ├── logging.rs         # 新增：日志初始化
│   │   ├── api/
│   │   │   ├── mod.rs
│   │   │   ├── handlers/
│   │   │   ├── middleware.rs  # 新增：中间件
│   │   │   └── docs.rs        # 新增：API文档
│   │   └── scheduler.rs       # 新增：定时任务
│   ├── config/                # 新增：配置文件
│   │   ├── default.yaml
│   │   ├── development.yaml
│   │   └── production.yaml
│   └── tests/                 # 新增：测试
│       ├── integration_tests.rs
│       └── api_tests.rs
├── migrations/                # 新增：数据库迁移
│   ├── 001_create_raw_table.sql
│   └── 002_create_standard_table.sql
└── docs/
    └── API.md                 # 新增：API文档
```

---

## 🎯 实施优先级

### 第一批（立即完成，今晚）
```
1. ✅ SeaORM替换SQLx
2. ✅ 错误处理框架
3. ✅ 日志系统
4. ✅ 配置管理
```

### 第二批（明天）
```
5. ✅ 数据库迁移
6. ✅ 数据验证
7. ✅ API文档
```

### 第三批（后天）
```
8. ✅ 定时任务
9. ✅ 监控指标
10. ✅ 测试框架
```

### 第四批（未来）
```
11. ✅ 缓存层优化
12. ✅ 性能调优
```

---

## 💡 总结

**刀哥，除了SeaORM，还需要完善：**

### 高优先级（必须）
1. ✅ **日志系统** - tracing
2. ✅ **错误处理** - thiserror + anyhow
3. ✅ **配置管理** - config + dotenvy
4. ✅ **数据库迁移** - SeaORM自带

### 中优先级（推荐）
5. ✅ **数据验证** - validator
6. ✅ **API文档** - utoipa
7. ✅ **定时任务** - tokio-cron-scheduler
8. ✅ **监控指标** - metrics + Prometheus
9. ✅ **测试框架** - tokio-test

### 低优先级（未来）
10. ✅ **缓存层** - Redis

---

**要不要现在就开始实施第一批（SeaORM + 错误 + 日志 + 配置）？**

预计2-3小时完成，系统会更加健壮！🌽✨
