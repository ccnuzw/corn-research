# 玉米研究系统V2 - 最小化技术栈方案

**核心理念**: 避免过度工程化，只加入真正必要的组件

---

## ⚠️ 用户关切

### 历史教训
```
旧系统问题：
- 133个Python脚本
- 1,581个CSV文件
- 1,871个Markdown文件
- 31步自动化流程
- 维护成本 > 数据本身价值
```

### 用户要求
```
✓ 简化、高效、明确
✓ 易用、美观
✓ 保留企业级能力
✓ 但不要为了企业级而企业级
✓ 个人研究为主
```

---

## 🎯 重新评估：哪些是真正必要的？

### ✅ 必须的（核心功能）

#### 1. SeaORM - 必须 ⭐⭐⭐⭐⭐
```
理由：
- 异步系统必需
- 替代SQLx，不是新增
- 减少代码量60%
- 提高开发效率

复杂度：低（减少复杂度）
```

#### 2. 基础错误处理 - 必须 ⭐⭐⭐⭐
```
理由：
- 程序稳定性基础
- 调试问题必需
- 几乎零学习成本

复杂度：极低
只需要：
- thiserror (自定义错误)
- 不需要复杂的错误链
```

#### 3. 基础日志 - 必须 ⭐⭐⭐⭐
```
理由：
- 调试问题必需
- 追踪采集过程
- println! 不够用

复杂度：极低
只需要：
- tracing (简化配置)
- 不需要日志持久化
- 不需要日志聚合
```

#### 4. 环境变量 - 必须 ⭐⭐⭐⭐⭐
```
理由：
- 数据库密码不能硬编码
- 本地/生产环境切换

复杂度：极低
只需要：
- dotenvy (读取.env)
- 不需要复杂配置系统
```

---

### ⚠️ 可选的（按需添加）

#### 5. 数据验证 - 可选 ⭐⭐⭐
```
现在：不急
理由：Python采集器已有基本验证
何时需要：前端表单输入时再加

复杂度：低
```

#### 6. API文档 - 可选 ⭐⭐
```
现在：不急
理由：只有你自己用，前后端都是你写
何时需要：团队协作时再加

复杂度：低
```

#### 7. 定时任务 - 可选 ⭐⭐⭐
```
现在：不急
理由：可以用系统cron或手动运行
何时需要：自动化需求明确时再加

复杂度：低
```

#### 8. 监控指标 - 可选 ⭐
```
现在：不需要
理由：个人系统，不是生产服务
何时需要：规模化时再考虑

复杂度：中
```

#### 9. 测试框架 - 可选 ⭐⭐
```
现在：不急
理由：MVP阶段，快速迭代
何时需要：功能稳定后再补

复杂度：低
```

#### 10. Redis缓存 - 可选 ⭐
```
现在：不需要
理由：数据量小，PostgreSQL够快
何时需要：性能瓶颈出现时再加

复杂度：低
```

---

## 🎯 最小化方案：只加4个

### 阶段1：立即完成（今晚）

#### 1. SeaORM（必须）
```toml
[dependencies]
sea-orm = { version = "0.12", features = [
    "sqlx-postgres",
    "runtime-tokio-native-tls",
    "macros"
]}
```

#### 2. 简化错误处理（必须）
```toml
[dependencies]
thiserror = "1.0"
```

```rust
// errors.rs (20行)
#[derive(Error, Debug)]
pub enum AppError {
    #[error("数据库错误: {0}")]
    Database(#[from] sea_orm::DbErr),
    
    #[error("采集器错误: {0}")]
    Collector(String),
}
```

#### 3. 简化日志（必须）
```toml
[dependencies]
tracing = "0.1"
tracing-subscriber = "0.3"
```

```rust
// main.rs (5行)
tracing_subscriber::fmt()
    .with_max_level(tracing::Level::INFO)
    .init();

// 使用 (1行)
tracing::info!("开始采集: {}", collector_id);
```

#### 4. 环境变量（必须）
```toml
[dependencies]
dotenvy = "0.15"
```

```bash
# .env (3行)
DATABASE_URL=postgresql://corn_user:***@localhost:15432/corn_research
SERVER_HOST=0.0.0.0
SERVER_PORT=18000
```

```rust
// main.rs (1行)
dotenvy::dotenv().ok();
let db_url = std::env::var("DATABASE_URL")?;
```

---

### 阶段2：按需添加（未来）

```
当遇到问题时再加：
- 需要自动化 → 定时任务
- 需要协作 → API文档
- 需要表单 → 数据验证
- 性能瓶颈 → Redis缓存
- 规模化 → 监控指标
```

---

## 📊 复杂度对比

### 原方案（10个组件）
```
代码增加：~2000行
学习成本：高
维护成本：高
风险：过度工程化
```

### 最小化方案（4个组件）
```
代码增加：~200行
学习成本：极低
维护成本：极低
风险：无
```

---

## 💡 具体实施

### 今晚（1小时）

#### Step 1: 添加依赖（5分钟）
```toml
# backend-rust/Cargo.toml
[dependencies]
axum = "0.7"
tokio = { version = "1", features = ["full"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

# 核心4件套
sea-orm = { version = "0.12", features = ["sqlx-postgres", "runtime-tokio-native-tls", "macros"] }
thiserror = "1.0"
tracing = "0.1"
tracing-subscriber = "0.3"
dotenvy = "0.15"

# PyO3
pyo3 = { version = "0.20", features = ["auto-initialize"] }

# 内部依赖
corn-infrastructure = { path = "../core-rust/corn-infrastructure" }
```

#### Step 2: 添加错误类型（10分钟）
```rust
// backend-rust/src/errors.rs
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("数据库错误: {0}")]
    Database(#[from] sea_orm::DbErr),
    
    #[error("Python错误: {0}")]
    Python(#[from] pyo3::PyErr),
    
    #[error("{0}")]
    Internal(String),
}

// Axum响应
impl axum::response::IntoResponse for AppError {
    fn into_response(self) -> axum::response::Response {
        (
            axum::http::StatusCode::INTERNAL_SERVER_ERROR,
            self.to_string()
        ).into_response()
    }
}
```

#### Step 3: 初始化日志（5分钟）
```rust
// backend-rust/src/main.rs
fn init_logging() {
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();
}

#[tokio::main]
async fn main() {
    init_logging();
    tracing::info!("玉米研究系统V2启动");
    // ...
}
```

#### Step 4: 环境变量（5分钟）
```bash
# .env
DATABASE_URL=postgresql://corn_user:corn_password_2026@localhost:15432/corn_research
SERVER_HOST=0.0.0.0
SERVER_PORT=18000
```

```rust
// main.rs
dotenvy::dotenv().ok();
let db_url = std::env::var("DATABASE_URL")?;
```

#### Step 5: 替换为SeaORM（30分钟）
```bash
# 生成实体
sea-orm-cli generate entity \
    -u $DATABASE_URL \
    -o src/entities

# 修改Repository使用SeaORM
```

---

## 📝 总结

### 最小化原则

**只加4个必需组件：**
1. ✅ SeaORM - 必须（替代SQLx）
2. ✅ thiserror - 必须（错误处理）
3. ✅ tracing - 必须（日志）
4. ✅ dotenvy - 必须（环境变量）

**其他6个暂不加：**
- ❌ validator
- ❌ utoipa
- ❌ tokio-cron-scheduler
- ❌ metrics
- ❌ 测试框架
- ❌ Redis客户端

### 优势
```
✓ 极简（只加200行代码）
✓ 聚焦核心功能
✓ 避免过度工程化
✓ 快速验证MVP
✓ 未来按需扩展
```

### 何时添加其他组件？
```
遇到问题时再说：
- 问题驱动，不是架构驱动
- 需求明确，不是预期需求
- 渐进式，不是一次到位
```

---

**刀哥，这个最小化方案如何？**

只加4个真正必要的：
- SeaORM（替代SQLx，减少复杂度）
- 错误处理（20行代码）
- 日志（5行代码）
- 环境变量（1行代码）

其他的，遇到问题再说！

**预计1小时完成，今晚就能跑通！** 🌽✨
