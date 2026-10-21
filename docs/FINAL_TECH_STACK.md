# 玉米研究系统V2 - 最终技术栈方案

**核心理念**: 必要性优先，避免过度工程化，但保留核心能力

---

## ✅ 最终确定：6个必需组件

### 核心4件套（基础）

#### 1. SeaORM - 数据访问 ⭐⭐⭐⭐⭐
```toml
sea-orm = { version = "0.12", features = [
    "sqlx-postgres",
    "runtime-tokio-native-tls",
    "macros",
    "with-chrono",
    "with-uuid"
]}
```

#### 2. thiserror - 错误处理 ⭐⭐⭐⭐⭐
```toml
thiserror = "1.0"
```

#### 3. tracing - 日志系统 ⭐⭐⭐⭐⭐
```toml
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }
```

#### 4. dotenvy - 环境变量 ⭐⭐⭐⭐⭐
```toml
dotenvy = "0.15"
```

---

### 核心功能2件套（必需）

#### 5. Redis客户端 - 缓存层 ⭐⭐⭐⭐⭐
```toml
redis = { version = "0.24", features = ["tokio-comp", "connection-manager"] }
```

**理由**:
```
✓ Redis容器已经在运行（16380端口）
✓ 查询结果缓存（减少数据库压力）
✓ 定时任务状态缓存
✓ 临时数据存储
```

**使用场景**:
```rust
// 缓存最新数据查询（5分钟过期）
async fn get_latest_cached(indicator: &str) -> Result<Vec<Data>> {
    let key = format!("latest:{}", indicator);
    
    // 尝试从Redis获取
    if let Ok(cached) = redis.get(&key).await {
        return Ok(serde_json::from_str(&cached)?);
    }
    
    // 从数据库查询
    let data = db.get_latest(indicator).await?;
    
    // 写入Redis
    redis.set_ex(&key, serde_json::to_string(&data)?, 300).await?;
    
    Ok(data)
}
```

#### 6. 定时任务 - 自动化 ⭐⭐⭐⭐⭐
```toml
tokio-cron-scheduler = "0.9"
```

**理由**:
```
✓ 每天自动采集（核心需求）
✓ Web端管理定时任务（用户明确要求）
✓ 任务状态监控
✓ 灵活调度
```

**功能**:
```rust
// 1. 定时采集
scheduler.add(Job::new_async("0 0 8 * * *", |_| {
    Box::pin(async {
        run_all_collectors().await;
    })
})?).await?;

// 2. Web端管理API
POST /api/scheduler/jobs      // 创建任务
GET  /api/scheduler/jobs      // 列出任务
PUT  /api/scheduler/jobs/:id  // 修改任务
DELETE /api/scheduler/jobs/:id // 删除任务
POST /api/scheduler/jobs/:id/run // 手动触发
```

---

## ❌ 暂不添加的4个（非必需）

### 1. validator - 数据验证
```
当前: 不急
原因: Python采集器已有基本验证
何时: 前端表单复杂时再加
```

### 2. utoipa - API文档
```
当前: 不急
原因: 只有你自己用
何时: 需要协作时再加
```

### 3. metrics - 监控指标
```
当前: 不急
原因: 个人系统，过度监控没必要
何时: 生产规模化时再加
```

### 4. 测试框架
```
当前: 不急
原因: MVP快速迭代阶段
何时: 功能稳定后补充
```

---

## 📦 完整依赖清单

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
tower-http = { version = "0.5", features = ["cors", "trace"] }

# 序列化
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

# 核心6件套
sea-orm = { version = "0.12", features = [
    "sqlx-postgres",
    "runtime-tokio-native-tls",
    "macros",
    "with-chrono",
    "with-uuid"
]}
thiserror = "1.0"
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }
dotenvy = "0.15"
redis = { version = "0.24", features = ["tokio-comp", "connection-manager"] }
tokio-cron-scheduler = "0.9"

# Python集成
pyo3 = { version = "0.20", features = ["auto-initialize"] }

# 工具
chrono = { version = "0.4", features = ["serde"] }
uuid = { version = "1.6", features = ["v4", "serde"] }

# 项目内部依赖
corn-infrastructure = { path = "../core-rust/corn-infrastructure" }
```

---

## 🏗️ 项目结构

```
backend-rust/
├── src/
│   ├── main.rs
│   ├── errors.rs              # 错误处理
│   ├── config.rs              # 环境变量配置
│   ├── cache/                 # Redis缓存层
│   │   ├── mod.rs
│   │   └── redis_client.rs
│   ├── scheduler/             # 定时任务
│   │   ├── mod.rs
│   │   ├── job_manager.rs     # 任务管理
│   │   └── jobs.rs            # 具体任务
│   └── api/
│       ├── mod.rs
│       ├── handlers/
│       │   ├── data.rs        # 数据查询
│       │   ├── collectors.rs  # 采集管理
│       │   └── scheduler.rs   # 任务管理 (新增)
│       └── middleware.rs
└── .env
```

---

## 🎯 实施计划

### 阶段1：基础设施（今晚，1.5小时）

#### Step 1: 核心4件套（30分钟）
```
1. 添加SeaORM + 错误 + 日志 + 环境变量
2. 生成数据库实体
3. 测试基础功能
```

#### Step 2: Redis集成（30分钟）
```rust
// cache/redis_client.rs
use redis::aio::ConnectionManager;

pub struct RedisCache {
    manager: ConnectionManager,
}

impl RedisCache {
    pub async fn new(url: &str) -> Result<Self> {
        let client = redis::Client::open(url)?;
        let manager = ConnectionManager::new(client).await?;
        Ok(Self { manager })
    }
    
    pub async fn get<T: DeserializeOwned>(&mut self, key: &str) -> Result<Option<T>> {
        let value: Option<String> = self.manager.get(key).await?;
        match value {
            Some(v) => Ok(Some(serde_json::from_str(&v)?)),
            None => Ok(None),
        }
    }
    
    pub async fn set_ex<T: Serialize>(
        &mut self,
        key: &str,
        value: &T,
        seconds: usize,
    ) -> Result<()> {
        let json = serde_json::to_string(value)?;
        self.manager.set_ex(key, json, seconds).await?;
        Ok(())
    }
}
```

#### Step 3: 定时任务（30分钟）
```rust
// scheduler/job_manager.rs
use tokio_cron_scheduler::{JobScheduler, Job};

pub struct JobManager {
    scheduler: JobScheduler,
}

impl JobManager {
    pub async fn new() -> Result<Self> {
        let scheduler = JobScheduler::new().await?;
        Ok(Self { scheduler })
    }
    
    pub async fn add_daily_collection(&self) -> Result<()> {
        // 每天早上8点采集
        self.scheduler.add(
            Job::new_async("0 0 8 * * *", |_uuid, _l| {
                Box::pin(async move {
                    tracing::info!("开始每日采集");
                    // 调用采集逻辑
                })
            })?
        ).await?;
        Ok(())
    }
    
    pub async fn start(&self) -> Result<()> {
        self.scheduler.start().await?;
        Ok(())
    }
}
```

---

### 阶段2：Web端任务管理（明天，2小时）

#### API接口
```rust
// api/handlers/scheduler.rs

// 获取所有任务
GET /api/scheduler/jobs
{
  "jobs": [
    {
      "id": "uuid",
      "name": "每日采集",
      "cron": "0 0 8 * * *",
      "enabled": true,
      "last_run": "2026-10-21T08:00:00Z",
      "next_run": "2026-10-22T08:00:00Z"
    }
  ]
}

// 创建任务
POST /api/scheduler/jobs
{
  "name": "博亚采集",
  "collector_id": "boyar_shandong_v2",
  "cron": "0 0 8 * * *"
}

// 手动触发
POST /api/scheduler/jobs/:id/run

// 启用/禁用
PUT /api/scheduler/jobs/:id/enable

// 删除任务
DELETE /api/scheduler/jobs/:id
```

#### 前端页面
```typescript
// 定时任务管理页面
/app/scheduler/page.tsx

- 任务列表（表格）
- 创建任务（模态框）
- 编辑任务（模态框）
- 手动触发按钮
- 启用/禁用开关
- 删除确认
```

---

## 💡 使用场景

### 1. Redis缓存
```rust
// 场景1: 最新数据查询（高频）
async fn get_latest_data(indicator: &str) -> Result<Vec<Data>> {
    let cache_key = format!("latest:{}:30days", indicator);
    
    // 先查缓存（5分钟过期）
    if let Some(data) = cache.get(&cache_key).await? {
        return Ok(data);
    }
    
    // 查数据库
    let data = db.get_latest(indicator, 30).await?;
    
    // 写缓存
    cache.set_ex(&cache_key, &data, 300).await?;
    
    Ok(data)
}

// 场景2: 任务状态缓存
cache.set("job:status:uuid", "running", 3600).await?;
```

### 2. 定时任务
```rust
// 场景1: 每天8点采集所有数据源
scheduler.add(Job::new_async("0 0 8 * * *", |_| {
    Box::pin(async {
        run_all_collectors().await;
    })
})?).await?;

// 场景2: 每小时采集高频数据源
scheduler.add(Job::new_async("0 0 * * * *", |_| {
    Box::pin(async {
        run_realtime_collectors().await;
    })
})?).await?;

// 场景3: Web端动态创建任务
async fn create_job(req: CreateJobRequest) -> Result<Job> {
    let job = Job::new_async(&req.cron, move |_| {
        Box::pin(async move {
            run_collector(&req.collector_id).await;
        })
    })?;
    
    scheduler.add(job).await?;
    Ok(job)
}
```

---

## 📊 最终方案对比

| 组件 | 必要性 | 代码量 | 复杂度 |
|------|--------|--------|--------|
| SeaORM | ⭐⭐⭐⭐⭐ | -60% | 低 |
| thiserror | ⭐⭐⭐⭐⭐ | 20行 | 极低 |
| tracing | ⭐⭐⭐⭐⭐ | 5行 | 极低 |
| dotenvy | ⭐⭐⭐⭐⭐ | 1行 | 极低 |
| **Redis** | ⭐⭐⭐⭐⭐ | 100行 | 低 |
| **定时任务** | ⭐⭐⭐⭐⭐ | 200行 | 低 |
| **总计** | | **+260行** | **低** |

---

## 📝 总结

### 最终确定：6个必需组件

**基础4件套**:
1. ✅ SeaORM
2. ✅ thiserror
3. ✅ tracing
4. ✅ dotenvy

**核心功能2件套**:
5. ✅ Redis（容器已有，必须用）
6. ✅ 定时任务（自动化核心，Web管理）

**暂不添加**:
- ❌ validator
- ❌ utoipa
- ❌ metrics
- ❌ 测试框架

---

## 🚀 实施时间

### 今晚（1.5小时）
```
1. 核心4件套（30分钟）
2. Redis集成（30分钟）
3. 定时任务基础（30分钟）
```

### 明天（2小时）
```
4. Web端任务管理API（1小时）
5. 前端任务管理页面（1小时）
```

---

**刀哥，这个最终方案：**
- ✅ Redis（容器已有，必须用）
- ✅ 定时任务（自动化核心 + Web管理）
- ✅ 总共只增加260行代码
- ✅ 保持系统简洁
- ✅ 满足核心需求

**完整方案已保存，现在要不要开始实施？** 🌽✨
