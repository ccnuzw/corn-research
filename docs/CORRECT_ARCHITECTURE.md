# 🏗️ 玉米研究系统V2 - 正确架构（方案2）

**日期**: 2026-10-20  
**决策**: 采用Rust Web服务作为后端

---

## ✅ 正确架构

```
┌─────────────────────────────────────────────┐
│         Next.js 14 前端                      │
│    (TypeScript + Shadcn/ui)                 │
│         用户界面 + 主题切换                   │
└─────────────────────────────────────────────┘
                    ↓ HTTP/WebSocket
┌─────────────────────────────────────────────┐
│       Rust Web服务 (Axum/Actix)              │
│        REST API + WebSocket                 │
├─────────────────────────────────────────────┤
│  • GET  /api/collectors                     │
│  • POST /api/collectors/{id}/run            │
│  • GET  /api/data/latest                    │
│  • WS   /ws/updates                         │
└─────────────────────────────────────────────┘
                    ↓
        ┌───────────┴───────────┐
        ↓                       ↓
┌──────────────────┐   ┌──────────────────┐
│  Rust DDD核心     │   │  Python采集器     │
│  corn-domain     │←──│ (通过PyO3调用)    │
│  corn-infra      │   │  BoyarCollector  │
│  - Price实体      │   │  SinaCollector   │
│  - 去重服务       │   └──────────────────┘
│  - 验证服务       │
└──────────────────┘
        ↓
┌─────────────────────────────────────────────┐
│   PostgreSQL + TimescaleDB + Redis          │
└─────────────────────────────────────────────┘
```

---

## 🎯 技术栈（修正）

| 层次 | 技术 | 职责 |
|------|------|------|
| **前端** | Next.js 14 + TypeScript | 用户界面 |
| **后端** | **Rust (Axum)** | Web服务 + REST API |
| **业务核心** | Rust DDD | 领域模型 + 业务逻辑 |
| **数据采集** | Python脚本 | 网站爬取（Rust调用） |
| **数据处理** | Rust | 去重、验证、转换 |
| **存储** | PostgreSQL + TimescaleDB | 时序数据 |
| **缓存** | Redis | 实时状态 |

---

## 📊 数据流

### 1. 用户触发采集
```
用户点击"开始采集" (Next.js)
  ↓
POST /api/collectors/boyar/run (HTTP)
  ↓
Rust Web服务接收
  ↓
调用 Python BoyarCollector (通过PyO3)
  ↓
Python返回原始数据
  ↓
Rust去重 + 验证
  ↓
保存到PostgreSQL
  ↓
返回JSON给前端
```

### 2. 实时更新
```
前端连接 WebSocket
  ↓
Rust推送采集进度
  ↓
前端实时显示
```

---

## 🔧 组件迁移清单

### ✅ 已完成（可直接使用）
- ✅ **Rust DDD核心** - corn-domain (Price, QualityScore, Location)
- ✅ **Rust数据处理** - corn-infrastructure (去重、验证)
- ✅ **Python采集器** - BoyarCollector, SinaCollector
- ✅ **Next.js前端** - 基础框架已搭建

### 📝 需要新建
- 📝 **Rust Web服务** - 使用Axum框架
  - REST API路由
  - WebSocket支持
  - 调用Python采集器的PyO3桥接
  - 数据库连接池
  
### ❌ 废弃
- ❌ FastAPI网关（不需要了）
- ❌ api-python目录（删除）

---

## 🚀 实施步骤

### Step 1: 创建Rust Web服务
```toml
# backend-rust/Cargo.toml
[dependencies]
axum = "0.7"
tokio = { version = "1", features = ["full"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
pyo3 = "0.20"
sqlx = { version = "0.7", features = ["postgres", "runtime-tokio"] }
tower = "0.4"
tower-http = { version = "0.5", features = ["cors"] }
```

### Step 2: 实现API路由
```rust
// GET /api/collectors - 获取采集器列表
// POST /api/collectors/{id}/run - 启动采集
// GET /api/data/latest - 获取最新数据
// WS /ws - WebSocket实时推送
```

### Step 3: PyO3桥接
```rust
// 从Rust调用Python采集器
let result = Python::with_gil(|py| {
    let module = py.import("collectors.boyar")?;
    let collector = module.getattr("BoyarCollector")?.call0()?;
    let data = collector.call_method0("collect")?;
    data.extract::<Vec<RawData>>()
})?;
```

---

## 💪 优势

1. **统一技术栈** - Rust为主，Python为辅
2. **高性能** - Rust处理所有请求
3. **简化架构** - 少一层Python网关
4. **更易维护** - 类型安全 + 编译时检查

---

**下一步**: 立即开始实施Rust Web服务！
