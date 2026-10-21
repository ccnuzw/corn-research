# 玉米研究系统V2 - 数据库集成技术方案

**时间**: 2026-10-21 03:35  
**状态**: 设计阶段

---

## 🎯 技术栈选型

### 已有基础设施
```yaml
数据库: PostgreSQL 15 + TimescaleDB (已部署)
端口: 15432 (Docker映射)
容器: postgres (运行中)
```

### Python端技术栈
```python
# 核心库
SQLAlchemy 2.0+        # ORM + 查询构建
psycopg2-binary        # PostgreSQL驱动
alembic               # 数据库迁移

# 可选增强
pydantic              # 数据验证（已有）
```

### Rust端技术栈（未来）
```rust
// 核心库
sqlx                  // 异步SQL库
tokio-postgres        // 异步驱动
sea-orm              // Rust ORM（可选）

// 当前阶段：只用Python写入，Rust读取
```

---

## 📊 数据库架构设计

### 基于CARF五段血缘

```
┌─────────────────────────────────────┐
│ RAW 原始层 (Python采集器写入)        │
│ - raw_collection_records            │
│ - 保留完整HTML/文本                  │
│ - 采集时间戳、来源URL                │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ STANDARD 标准层 (Python转换)         │
│ - market_facts_standard             │
│ - 业务日期、指标名、数值              │
│ - 质量分级、口径说明                  │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ DERIVED 派生层 (Rust计算)            │
│ - market_artifacts                  │
│ - 聚合指标、趋势计算                  │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ RUN/DECISION (未来)                  │
│ - 场景运行、决策记录                  │
└─────────────────────────────────────┘
```

---

## 🗄️ 表结构设计

### 1. RAW层：raw_collection_records

```sql
CREATE TABLE raw_collection_records (
    -- 主键和索引
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 采集信息
    collector_id VARCHAR(100) NOT NULL,     -- 'boyar_shandong_v2'
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ,               -- 数据发布时间
    
    -- 来源信息
    source_url TEXT NOT NULL,
    source_type VARCHAR(50),                -- 'commercial_primary'
    
    -- 原始内容（二选一）
    raw_html TEXT,                          -- 完整HTML
    raw_text TEXT,                          -- 纯文本
    
    -- 数据类型
    content_type VARCHAR(50),               -- 'arrivals', 'spot_price'
    
    -- 业务数据（从JSON提取）
    business_date DATE NOT NULL,
    indicator_name VARCHAR(200) NOT NULL,   -- '山东深加工到车量'
    value NUMERIC,
    unit VARCHAR(20),
    region VARCHAR(100),
    
    -- 元数据
    metadata JSONB,                         -- 原JSON的metadata字段
    
    -- 去重标识
    dedup_key VARCHAR(500) UNIQUE,          -- collector_id + business_date + indicator
    
    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_raw_collector ON raw_collection_records(collector_id, business_date DESC);
CREATE INDEX idx_raw_indicator ON raw_collection_records(indicator_name, business_date DESC);
CREATE INDEX idx_raw_collected ON raw_collection_records(collected_at DESC);
CREATE INDEX idx_raw_business_date ON raw_collection_records(business_date DESC);
```

### 2. STANDARD层：market_facts_standard

```sql
CREATE TABLE market_facts_standard (
    -- 主键
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 关联RAW层
    raw_record_id UUID REFERENCES raw_collection_records(id),
    
    -- CARF分类
    artifact_type VARCHAR(50),              -- 'ART-MKT-001'
    domain VARCHAR(100),                    -- '区域流通'
    
    -- 业务数据
    business_date DATE NOT NULL,
    indicator_name VARCHAR(200) NOT NULL,
    value NUMERIC NOT NULL,
    unit VARCHAR(20) NOT NULL,
    region VARCHAR(100),
    
    -- 质量分级（CARF）
    quality_grade CHAR(1) NOT NULL,         -- 'A', 'B', 'C', 'D'
    caliber TEXT,                           -- 口径说明
    confidence VARCHAR(20),                 -- 'high', 'medium', 'low'
    
    -- 时间戳
    disclosure_time TIMESTAMPTZ,            -- 披露时间
    validated_at TIMESTAMPTZ,               -- 验证时间
    
    -- 版本控制（CARF要求）
    version INT DEFAULT 1,
    is_revision BOOLEAN DEFAULT FALSE,
    revision_reason TEXT,
    
    -- 去重
    dedup_key VARCHAR(500) UNIQUE,
    
    -- 审计
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_standard_business ON market_facts_standard(business_date DESC, indicator_name);
CREATE INDEX idx_standard_quality ON market_facts_standard(quality_grade, business_date DESC);
CREATE INDEX idx_standard_artifact ON market_facts_standard(artifact_type, business_date DESC);
```

### 3. 视图：最新数据快速查询

```sql
CREATE VIEW v_latest_market_data AS
SELECT DISTINCT ON (indicator_name, region)
    indicator_name,
    region,
    business_date,
    value,
    unit,
    quality_grade,
    collected_at,
    source_url
FROM raw_collection_records
WHERE business_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY indicator_name, region, business_date DESC, collected_at DESC;
```

---

## 🔧 实现方式

### 方案A：纯Python实现（推荐，第一阶段）

#### 优点
- ✅ 快速实现（2-3天）
- ✅ 采集器无需改动
- ✅ 完全控制数据流
- ✅ 易于调试

#### 架构
```
采集器 → JSON文件 → Python脚本 → PostgreSQL
                ↓
            保留归档
```

#### 实现步骤
```python
# 1. 定义SQLAlchemy模型
class RawCollectionRecord(Base):
    __tablename__ = 'raw_collection_records'
    id = Column(UUID, primary_key=True)
    collector_id = Column(String(100))
    # ...

# 2. 读取JSON文件
with open('data/raw/boyar_*.json') as f:
    data = json.load(f)

# 3. 写入数据库
for record in data['records']:
    db_record = RawCollectionRecord(
        collector_id=data['collector_id'],
        business_date=record['business_date'],
        # ...
    )
    session.add(db_record)
session.commit()

# 4. JSON文件归档（不删除）
shutil.move('data/raw/*.json', 'data/archive/')
```

---

### 方案B：采集器直接写数据库（第二阶段）

#### 优点
- ✅ 实时写入
- ✅ 无中间文件
- ✅ 事务保证

#### 架构
```
采集器 → PostgreSQL → 备份JSON
```

#### 实现步骤
```python
# 修改BaseCollector
class BaseCollector(ABC):
    def __init__(self, db_session=None):
        self.db = db_session
    
    def collect(self) -> List[RawDataRecord]:
        records = self._fetch_data()
        
        # 写入数据库
        if self.db:
            for record in records:
                db_record = RawCollectionRecord.from_raw(record)
                self.db.add(db_record)
            self.db.commit()
        
        # 仍然返回记录（兼容性）
        return records
```

---

### 方案C：Rust后端读取（第三阶段）

#### 架构
```
Next.js前端 → Rust Axum API → PostgreSQL
                           ↑
                    Python采集器写入
```

#### Rust API示例
```rust
// GET /api/data/latest?indicator=山东到车
async fn get_latest_data(
    Query(params): Query<DataQuery>,
    State(pool): State<PgPool>,
) -> Result<Json<Vec<MarketData>>, AppError> {
    let rows = sqlx::query_as!(
        MarketData,
        r#"
        SELECT * FROM raw_collection_records
        WHERE indicator_name = $1
        ORDER BY business_date DESC
        LIMIT 30
        "#,
        params.indicator
    )
    .fetch_all(&pool)
    .await?;
    
    Ok(Json(rows))
}
```

---

## 📅 实施计划

### Phase 1: Python基础（2天）
**目标**: JSON → PostgreSQL基本流程

- [ ] Day 1
  - [x] 设计表结构
  - [ ] 编写SQLAlchemy模型
  - [ ] 实现基础写入脚本
  - [ ] 测试单条数据写入

- [ ] Day 2
  - [ ] 批量导入历史JSON
  - [ ] 实现增量同步
  - [ ] 添加去重逻辑
  - [ ] 验证数据完整性

### Phase 2: 采集器集成（1天）
**目标**: 采集器直接写数据库

- [ ] Day 3
  - [ ] 修改BaseCollector支持数据库
  - [ ] 更新daily_collection.py
  - [ ] 保留JSON备份机制
  - [ ] 端到端测试

### Phase 3: Rust API（2-3天）
**目标**: Web界面可以读取数据

- [ ] Day 4-5
  - [ ] Rust连接PostgreSQL
  - [ ] 实现查询API
  - [ ] 前端集成测试
  - [ ] 性能优化

---

## 🔒 数据完整性保证

### 1. 去重策略
```sql
-- 使用唯一约束
dedup_key = f"{collector_id}_{business_date}_{indicator_name}"

-- 冲突处理
ON CONFLICT (dedup_key) DO UPDATE SET
    updated_at = NOW(),
    metadata = EXCLUDED.metadata
```

### 2. 事务保证
```python
with db.begin():
    # 批量插入
    db.bulk_insert_mappings(RawCollectionRecord, records)
    # 失败则全部回滚
```

### 3. 备份策略
- RAW层：JSON文件归档（永久保留）
- 数据库：每日备份
- TimescaleDB：自动压缩历史数据

---

## 📊 预期效果

### 性能指标
- 写入速度: >1000条/秒
- 查询延迟: <100ms
- 存储空间: ~1MB/1000条

### 数据查询示例
```python
# 查询最近30天山东到车
records = session.query(RawCollectionRecord)\
    .filter(
        RawCollectionRecord.indicator_name == '山东深加工到车量',
        RawCollectionRecord.business_date >= date.today() - timedelta(days=30)
    )\
    .order_by(RawCollectionRecord.business_date.desc())\
    .all()

# 统计数据质量
quality_stats = session.query(
    MarketFactsStandard.quality_grade,
    func.count()
).group_by(MarketFactsStandard.quality_grade).all()
```

---

## 🚀 下一步

**推荐从Phase 1开始**:
1. 先实现SQLAlchemy模型
2. 编写导入脚本
3. 测试历史数据导入
4. 验证查询性能

**刀哥，这个方案如何？要不要现在就开始实现Phase 1？** 🌽✨
