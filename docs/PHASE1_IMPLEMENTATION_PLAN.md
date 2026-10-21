# Phase 1 实施计划 - Rust基础设施

**目标**: 建立Rust DDD基础 + PyO3 Bridge + PostgreSQL连接

---

## 当前状态检查

### 已有结构
```
/Users/apple/CornV2/
├── core-rust/                 # Rust DDD核心
│   ├── corn-domain/          # 领域层（已有部分）
│   ├── corn-infrastructure/  # 基础设施层（已有部分）
│   └── corn-python/          # PyO3桥接（已有框架）
├── backend-rust/             # Axum Web服务器
├── collectors-python/        # Python采集器（已完成）
└── docker-compose.yml        # PostgreSQL已运行
```

---

## Phase 1.1: 设置Rust Workspace（30分钟）

### 任务
1. [ ] 创建统一的workspace Cargo.toml
2. [ ] 组织DDD分层结构
3. [ ] 配置依赖版本

### 目标结构
```
core-rust/
├── Cargo.toml                    # Workspace配置
├── corn-domain/                  # Domain层
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs
│       ├── entities/
│       │   ├── mod.rs
│       │   └── market_fact.rs    # 新增
│       ├── value_objects/
│       │   ├── mod.rs
│       │   ├── indicator.rs      # 新增
│       │   └── quality_grade.rs  # 新增
│       └── services/
│           ├── mod.rs
│           └── collection_orchestrator.rs  # 新增
├── corn-infrastructure/          # Infrastructure层
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs
│       ├── python_bridge.rs      # 新增（核心）
│       └── repositories/
│           ├── mod.rs
│           └── postgres_repo.rs  # 新增
└── corn-application/             # Application层（新增）
    ├── Cargo.toml
    └── src/
        ├── lib.rs
        └── dto/
            ├── mod.rs
            └── collection_result.rs
```

---

## Phase 1.2: 实现PyO3 Bridge（1小时）

### 核心文件: `corn-infrastructure/src/python_bridge.rs`

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;
use chrono::NaiveDate;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawRecord {
    pub business_date: NaiveDate,
    pub indicator_name: String,
    pub value: f64,
    pub unit: String,
    pub region: String,
    pub source_url: String,
    pub original_text: String,
    pub collector_id: String,
}

pub struct PyO3Bridge;

impl PyO3Bridge {
    pub fn new() -> Self {
        Self
    }
    
    pub fn collect(&self, collector_id: &str) -> PyResult<Vec<RawRecord>> {
        Python::with_gil(|py| {
            // 设置Python路径
            let sys = py.import("sys")?;
            let path = sys.getattr("path")?;
            path.call_method1("append", ("collectors-python",))?;
            
            // 导入采集器模块
            let collectors = py.import("collectors")?;
            
            // 获取采集器类
            let collector_class = match collector_id {
                "boyar_shandong_v2" => {
                    collectors.getattr("BoyarCollectorV2")?
                }
                "sina_north_port" => {
                    collectors.getattr("SinaCollectorV2")?
                }
                "mock_test" => {
                    collectors.getattr("MockCollector")?
                }
                _ => {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Unknown collector: {}", collector_id)
                    ));
                }
            };
            
            // 实例化采集器
            let collector = collector_class.call0()?;
            
            // 调用collect方法
            let py_records = collector.call_method0("collect")?;
            
            // 转换为Rust结构
            self.convert_records(py, py_records)
        })
    }
    
    fn convert_records(
        &self,
        py: Python,
        py_records: &PyAny,
    ) -> PyResult<Vec<RawRecord>> {
        let mut records = Vec::new();
        
        // 遍历Python返回的列表
        for item in py_records.iter()? {
            let record = self.convert_single_record(py, item?)?;
            records.push(record);
        }
        
        Ok(records)
    }
    
    fn convert_single_record(
        &self,
        _py: Python,
        py_record: &PyAny,
    ) -> PyResult<RawRecord> {
        // 提取字段
        let business_date_str: String = py_record
            .getattr("business_date")?
            .extract()?;
        
        let business_date = NaiveDate::parse_from_str(
            &business_date_str,
            "%Y-%m-%d"
        ).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Invalid date format: {}", e)
            )
        })?;
        
        Ok(RawRecord {
            business_date,
            indicator_name: py_record.getattr("indicator")?.extract()?,
            value: py_record.getattr("value")?.extract()?,
            unit: py_record.getattr("unit")?.extract()?,
            region: py_record.getattr("region")?.extract()?,
            source_url: py_record.getattr("source_url")?.extract()?,
            original_text: py_record.getattr("original_text")?.extract()?,
            collector_id: py_record
                .getattr("metadata")?
                .get_item("collector_id")?
                .extract()?,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_python_bridge_mock() {
        let bridge = PyO3Bridge::new();
        let records = bridge.collect("mock_test").unwrap();
        
        assert!(!records.is_empty());
        assert_eq!(records[0].unit, "台");
    }
}
```

---

## Phase 1.3: PostgreSQL连接（30分钟）

### 核心文件: `corn-infrastructure/src/repositories/postgres_repo.rs`

```rust
use sqlx::{PgPool, postgres::PgPoolOptions};
use async_trait::async_trait;
use uuid::Uuid;
use chrono::{NaiveDate, Utc};

use crate::python_bridge::RawRecord;

pub struct PostgresRepository {
    pool: PgPool,
}

impl PostgresRepository {
    pub async fn new(database_url: &str) -> Result<Self, sqlx::Error> {
        let pool = PgPoolOptions::new()
            .max_connections(5)
            .connect(database_url)
            .await?;
        
        Ok(Self { pool })
    }
    
    pub async fn save_raw_records(
        &self,
        records: &[RawRecord],
    ) -> Result<usize, sqlx::Error> {
        let mut tx = self.pool.begin().await?;
        let mut saved = 0;
        
        for record in records {
            let id = Uuid::new_v4();
            let dedup_key = format!(
                "{}_{}_{}",
                record.collector_id,
                record.business_date,
                record.indicator_name
            );
            
            let result = sqlx::query!(
                r#"
                INSERT INTO raw_collection_records (
                    id, collector_id, business_date,
                    indicator_name, value, unit, region,
                    source_url, original_text,
                    dedup_key, collected_at, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (dedup_key) DO NOTHING
                "#,
                id,
                record.collector_id,
                record.business_date,
                record.indicator_name,
                record.value,
                record.unit,
                record.region,
                record.source_url,
                record.original_text,
                dedup_key,
                Utc::now(),
                Utc::now(),
            )
            .execute(&mut *tx)
            .await?;
            
            if result.rows_affected() > 0 {
                saved += 1;
            }
        }
        
        tx.commit().await?;
        Ok(saved)
    }
}
```

---

## Phase 1.4: 数据库初始化脚本（15分钟）

### 文件: `migrations/001_create_raw_table.sql`

```sql
-- RAW层表结构
CREATE TABLE IF NOT EXISTS raw_collection_records (
    id UUID PRIMARY KEY,
    collector_id VARCHAR(100) NOT NULL,
    business_date DATE NOT NULL,
    indicator_name VARCHAR(200) NOT NULL,
    value NUMERIC NOT NULL,
    unit VARCHAR(20) NOT NULL,
    region VARCHAR(100),
    
    -- 溯源
    source_url TEXT NOT NULL,
    original_text TEXT,
    
    -- 去重
    dedup_key VARCHAR(500) UNIQUE NOT NULL,
    
    -- 时间戳
    collected_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_raw_indicator_date 
    ON raw_collection_records(indicator_name, business_date DESC);

CREATE INDEX IF NOT EXISTS idx_raw_collector 
    ON raw_collection_records(collector_id, collected_at DESC);

CREATE INDEX IF NOT EXISTS idx_raw_business_date 
    ON raw_collection_records(business_date DESC);
```

---

## Phase 1.5: 端到端测试（30分钟）

### 测试文件: `core-rust/tests/integration_test.rs`

```rust
use corn_infrastructure::python_bridge::PyO3Bridge;
use corn_infrastructure::repositories::PostgresRepository;

#[tokio::test]
async fn test_end_to_end_collection() {
    // 1. 通过PyO3调用Python采集器
    let bridge = PyO3Bridge::new();
    let records = bridge.collect("mock_test").unwrap();
    
    assert!(!records.is_empty());
    println!("✓ Python采集成功: {} 条记录", records.len());
    
    // 2. 连接PostgreSQL
    let db_url = "postgresql://corn_user:corn_password_2026@localhost:15432/corn_research";
    let repo = PostgresRepository::new(db_url).await.unwrap();
    
    println!("✓ PostgreSQL连接成功");
    
    // 3. 写入数据库
    let saved = repo.save_raw_records(&records).await.unwrap();
    
    println!("✓ 数据库写入成功: {} 条新记录", saved);
    
    assert!(saved > 0);
}
```

---

## 时间估算

| 任务 | 预计时间 | 描述 |
|------|---------|------|
| 1.1 Workspace设置 | 30分钟 | 配置Cargo.toml |
| 1.2 PyO3 Bridge | 1小时 | 核心桥接代码 |
| 1.3 PostgreSQL连接 | 30分钟 | sqlx配置 |
| 1.4 数据库初始化 | 15分钟 | SQL脚本 |
| 1.5 端到端测试 | 30分钟 | 集成测试 |
| **总计** | **约2.5小时** | |

---

## 立即开始

**刀哥，现在开始第一步：检查并配置Rust workspace！**
