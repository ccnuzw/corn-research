# 玉米研究系统V2 - Rust DDD架构设计

**核心理念**: Python只负责采集，Rust DDD掌控所有业务逻辑

---

## 🎯 架构原则

### 明确的职责分离
```
Python采集器:
  ✓ HTTP请求、HTML解析
  ✓ 提取原始数据
  ✓ 返回标准化RawDataRecord
  ✗ 不写数据库
  ✗ 不做业务逻辑
  ✗ 不做数据验证

Rust DDD核心:
  ✓ 通过PyO3调用Python采集器
  ✓ 接收RawDataRecord并验证
  ✓ 写入PostgreSQL
  ✓ 实现所有业务逻辑
  ✓ 提供REST API给前端
```

---

## 🏗️ 完整架构图

```
┌──────────────────────────────────────────────────────────┐
│                     Next.js Frontend                      │
│                   (localhost:3080)                        │
└────────────────────┬─────────────────────────────────────┘
                     │ HTTP REST API
                     ↓
┌──────────────────────────────────────────────────────────┐
│               Rust Axum Web Server                        │
│                  (localhost:18000)                        │
│  ┌────────────────────────────────────────────────────┐  │
│  │          Application Layer (Axum Handlers)         │  │
│  │  - GET /api/data/latest                           │  │
│  │  - POST /api/collectors/run                       │  │
│  │  - GET /api/stats/quality                         │  │
│  └───────────────────┬────────────────────────────────┘  │
│                      ↓                                    │
│  ┌────────────────────────────────────────────────────┐  │
│  │         Domain Layer (DDD Core)                    │  │
│  │  Entities:                                         │  │
│  │  - MarketFact (业务实体)                           │  │
│  │  - CollectionTask (采集任务)                       │  │
│  │  - QualityScore (质量评分)                         │  │
│  │                                                    │  │
│  │  Services:                                         │  │
│  │  - CollectionOrchestrator (采集编排)              │  │
│  │  - DataValidator (数据验证)                        │  │
│  │  - QualityAssessor (质量评估)                     │  │
│  └───────────────────┬────────────────────────────────┘  │
│                      ↓                                    │
│  ┌────────────────────────────────────────────────────┐  │
│  │      Infrastructure Layer                          │  │
│  │  - PostgreSQL Repository                          │  │
│  │  - PyO3 Collector Bridge ←─────┐                  │  │
│  │  - Redis Cache                  │                  │  │
│  └─────────────────────────────────┼──────────────────┘  │
└──────────────────────────────────┼─────────────────────┘
                                    │ PyO3 FFI
                                    ↓
                    ┌────────────────────────────┐
                    │   Python Collectors        │
                    │  (只负责采集)               │
                    │  - BoyarCollectorV2        │
                    │  - SinaCollectorV2         │
                    │  - MockCollector           │
                    └────────────────────────────┘
                                    ↓
                         Internet (数据源)
```

---

## 📦 Rust DDD分层架构

### 1. Domain Layer (核心业务逻辑)

#### Entities (实体)
```rust
// core-rust/src/domain/entities/market_fact.rs
pub struct MarketFact {
    id: Uuid,
    business_date: NaiveDate,
    indicator: Indicator,
    value: Decimal,
    unit: Unit,
    region: Region,
    quality: QualityGrade,
    lineage: DataLineage,  // CARF血缘追踪
}

impl MarketFact {
    // 业务规则：只能从RAW层提升
    pub fn from_raw(raw: RawRecord) -> Result<Self, DomainError> {
        // 验证业务规则
        Self::validate_business_rules(&raw)?;
        // 质量评分
        let quality = QualityAssessor::assess(&raw)?;
        // 创建实体
        Ok(Self { /* ... */ })
    }
}

// core-rust/src/domain/entities/collection_task.rs
pub struct CollectionTask {
    id: Uuid,
    collector_id: String,
    status: TaskStatus,
    scheduled_at: DateTime<Utc>,
    completed_at: Option<DateTime<Utc>>,
}
```

#### Value Objects (值对象)
```rust
// core-rust/src/domain/value_objects.rs
#[derive(Debug, Clone)]
pub struct Indicator {
    name: String,
    category: IndicatorCategory,
}

#[derive(Debug, Clone)]
pub enum QualityGrade {
    A,  // 官方权威
    B,  // 行业主流
    C,  // 公开可信
    D,  // 待验证
}

#[derive(Debug, Clone)]
pub struct DataLineage {
    stage: LineageStage,  // RAW/STANDARD/DERIVED
    source_url: String,
    collected_at: DateTime<Utc>,
    version: i32,
}
```

#### Domain Services (领域服务)
```rust
// core-rust/src/domain/services/collection_orchestrator.rs
pub struct CollectionOrchestrator {
    python_bridge: Arc<PyO3Bridge>,
    validator: Arc<DataValidator>,
    repo: Arc<dyn MarketDataRepository>,
}

impl CollectionOrchestrator {
    pub async fn run_collection(
        &self,
        collector_id: &str,
    ) -> Result<CollectionResult> {
        // 1. 通过PyO3调用Python采集器
        let raw_records = self.python_bridge
            .collect(collector_id)
            .await?;
        
        // 2. 验证数据
        let validated = self.validator
            .validate_batch(&raw_records)?;
        
        // 3. 转换为领域实体
        let facts: Vec<MarketFact> = validated
            .into_iter()
            .map(|r| MarketFact::from_raw(r))
            .collect::<Result<_>>()?;
        
        // 4. 持久化到数据库
        self.repo.save_batch(&facts).await?;
        
        Ok(CollectionResult {
            total: facts.len(),
            succeeded: facts.len(),
            failed: 0,
        })
    }
}

// core-rust/src/domain/services/data_validator.rs
pub struct DataValidator;

impl DataValidator {
    pub fn validate_batch(
        &self,
        records: &[RawRecord],
    ) -> Result<Vec<ValidatedRecord>> {
        records
            .iter()
            .map(|r| self.validate_single(r))
            .collect()
    }
    
    fn validate_single(&self, r: &RawRecord) -> Result<ValidatedRecord> {
        // 业务规则验证
        if r.value < 0.0 {
            return Err(ValidationError::NegativeValue);
        }
        
        // 日期合理性
        if r.business_date > Utc::now().date_naive() {
            return Err(ValidationError::FutureDate);
        }
        
        Ok(ValidatedRecord::from(r))
    }
}
```

---

### 2. Infrastructure Layer (基础设施)

#### PyO3 Bridge (Python桥接)
```rust
// core-rust/src/infrastructure/python_bridge.rs
use pyo3::prelude::*;

pub struct PyO3Bridge {
    python: GilGuard,
}

impl PyO3Bridge {
    pub async fn collect(
        &self,
        collector_id: &str,
    ) -> Result<Vec<RawRecord>> {
        Python::with_gil(|py| {
            // 导入Python模块
            let collectors = py.import("collectors")?;
            
            // 获取采集器类
            let collector_class = match collector_id {
                "boyar_shandong_v2" => collectors.getattr("BoyarCollectorV2")?,
                "sina_north_port" => collectors.getattr("SinaCollectorV2")?,
                "mock_test" => collectors.getattr("MockCollector")?,
                _ => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Unknown collector: {}", collector_id)
                )),
            };
            
            // 实例化采集器
            let collector = collector_class.call0()?;
            
            // 调用collect方法
            let records = collector.call_method0("collect")?;
            
            // 转换为Rust结构
            self.convert_to_rust_records(records)
        })
    }
    
    fn convert_to_rust_records(
        &self,
        py_records: &PyAny,
    ) -> Result<Vec<RawRecord>> {
        let records: Vec<RawRecord> = py_records
            .extract::<Vec<PyDict>>()?
            .into_iter()
            .map(|dict| RawRecord {
                business_date: dict.get_item("business_date")?.extract()?,
                indicator_name: dict.get_item("indicator")?.extract()?,
                value: dict.get_item("value")?.extract()?,
                unit: dict.get_item("unit")?.extract()?,
                // ...
            })
            .collect::<Result<_>>()?;
        
        Ok(records)
    }
}
```

#### PostgreSQL Repository
```rust
// core-rust/src/infrastructure/repositories/market_data_repo.rs
use sqlx::{PgPool, QueryBuilder};

pub struct PostgresMarketDataRepository {
    pool: PgPool,
}

impl PostgresMarketDataRepository {
    pub async fn save_batch(
        &self,
        facts: &[MarketFact],
    ) -> Result<()> {
        let mut tx = self.pool.begin().await?;
        
        for fact in facts {
            sqlx::query!(
                r#"
                INSERT INTO raw_collection_records (
                    id, collector_id, business_date,
                    indicator_name, value, unit, region,
                    quality_grade, source_url, metadata,
                    collected_at, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (dedup_key) DO NOTHING
                "#,
                fact.id,
                fact.indicator.collector_id(),
                fact.business_date,
                fact.indicator.name(),
                fact.value,
                fact.unit.to_string(),
                fact.region.to_string(),
                fact.quality.to_string(),
                fact.lineage.source_url,
                sqlx::types::Json(&fact.metadata),
                fact.lineage.collected_at,
                Utc::now(),
            )
            .execute(&mut *tx)
            .await?;
        }
        
        tx.commit().await?;
        Ok(())
    }
    
    pub async fn get_latest(
        &self,
        indicator: &str,
        days: i32,
    ) -> Result<Vec<MarketFact>> {
        let rows = sqlx::query_as!(
            MarketFactRow,
            r#"
            SELECT * FROM raw_collection_records
            WHERE indicator_name = $1
              AND business_date >= CURRENT_DATE - $2
            ORDER BY business_date DESC
            "#,
            indicator,
            days
        )
        .fetch_all(&self.pool)
        .await?;
        
        rows.into_iter()
            .map(MarketFact::from_row)
            .collect()
    }
}
```

---

### 3. Application Layer (应用层)

#### REST API Handlers
```rust
// backend-rust/src/api/handlers/data.rs
use axum::{
    extract::{Query, State},
    Json,
};

#[derive(Deserialize)]
pub struct DataQuery {
    indicator: String,
    days: Option<i32>,
}

pub async fn get_latest_data(
    Query(q): Query<DataQuery>,
    State(app): State<AppState>,
) -> Result<Json<Vec<MarketDataDto>>, ApiError> {
    let facts = app.market_data_repo
        .get_latest(&q.indicator, q.days.unwrap_or(30))
        .await?;
    
    let dtos: Vec<MarketDataDto> = facts
        .into_iter()
        .map(|f| f.into())
        .collect();
    
    Ok(Json(dtos))
}

// POST /api/collectors/run
#[derive(Deserialize)]
pub struct RunCollectorRequest {
    collector_id: String,
}

pub async fn run_collector(
    State(app): State<AppState>,
    Json(req): Json<RunCollectorRequest>,
) -> Result<Json<CollectionResult>, ApiError> {
    let result = app.orchestrator
        .run_collection(&req.collector_id)
        .await?;
    
    Ok(Json(result))
}
```

---

## 🗄️ 数据库表设计（Rust视角）

```sql
-- RAW层：Python采集的原始数据
CREATE TABLE raw_collection_records (
    id UUID PRIMARY KEY,
    collector_id VARCHAR(100) NOT NULL,
    business_date DATE NOT NULL,
    indicator_name VARCHAR(200) NOT NULL,
    value NUMERIC NOT NULL,
    unit VARCHAR(20) NOT NULL,
    region VARCHAR(100),
    
    -- CARF质量分级
    quality_grade CHAR(1) NOT NULL CHECK (quality_grade IN ('A','B','C','D')),
    
    -- 溯源信息
    source_url TEXT NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL,
    
    -- 元数据（JSONB）
    metadata JSONB,
    
    -- 去重键
    dedup_key VARCHAR(500) UNIQUE,
    
    -- 审计
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_raw_indicator_date ON raw_collection_records(indicator_name, business_date DESC);
CREATE INDEX idx_raw_collector ON raw_collection_records(collector_id, collected_at DESC);
CREATE INDEX idx_raw_quality ON raw_collection_records(quality_grade, business_date DESC);
```

---

## 🔧 技术栈总结

### Python端（采集层）
```python
# 依赖（最小化）
requests
beautifulsoup4
lxml

# 职责
- HTTP请求
- HTML解析
- 数据提取
- 返回Python dict/dataclass
```

### Rust端（DDD核心）
```rust
// Cargo.toml
[dependencies]
# Web框架
axum = "0.7"
tokio = { version = "1", features = ["full"] }
tower = "0.4"
tower-http = "0.5"

# 数据库
sqlx = { version = "0.7", features = ["postgres", "uuid", "chrono", "json"] }

# Python桥接
pyo3 = { version = "0.20", features = ["auto-initialize"] }

# 序列化
serde = { version = "1", features = ["derive"] }
serde_json = "1"

# 日期时间
chrono = { version = "0.4", features = ["serde"] }

// 职责
- 调用Python采集器（PyO3）
- 数据验证和转换
- 写入PostgreSQL
- 实现业务逻辑
- 提供REST API
```

---

## 📅 实施计划

### Phase 1: Rust基础设施（2-3天）
1. [ ] 设置Rust workspace结构
2. [ ] 实现PyO3 Bridge基础
3. [ ] 连接PostgreSQL
4. [ ] 测试Python调用

### Phase 2: DDD核心（3-4天）
5. [ ] 定义Domain Entities
6. [ ] 实现Domain Services
7. [ ] 实现Repository
8. [ ] 单元测试

### Phase 3: REST API（2天）
9. [ ] Axum路由设置
10. [ ] 实现API Handlers
11. [ ] 前端集成

---

**刀哥，这个架构如何？**

核心理念：
- ✅ Python只负责采集（纯粹的数据抓取工具）
- ✅ Rust DDD掌控一切业务逻辑
- ✅ 通过PyO3实现清晰的边界
- ✅ PostgreSQL直接由Rust管理

**要不要我现在就开始实现Phase 1？** 🌽✨
