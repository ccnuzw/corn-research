# 🛠️ 玉米研究系统 V2 - 开发者指南

**版本**: v2.0.0  
**最后更新**: 2026-10-22

---

## 📑 目录

- [系统架构](#系统架构)
- [开发环境设置](#开发环境设置)
- [开发指南](#开发指南)
- [贡献指南](#贡献指南)
- [附录](#附录)

---

## 系统架构

### 整体架构

玉米研究系统采用**分层微服务架构**，由以下核心组件构成：

```
┌──────────────────────────────────────────────────────────┐
│                    前端层 (Presentation)                  │
│              Next.js 14 + React 18 + TypeScript           │
│        SSR/SSG | 响应式设计 | 实时更新 | 数据可视化       │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP REST API (JSON)
┌────────────────────────▼─────────────────────────────────┐
│                    应用层 (Application)                   │
│                Rust Backend + Axum Framework              │
│        路由处理 | 业务逻辑 | 异步任务 | 权限验证         │
└────────────────────────┬─────────────────────────────────┘
                         │ Command Execution
┌────────────────────────▼─────────────────────────────────┐
│                    采集层 (Collectors)                    │
│              Python 3.11 + 动态加载机制                   │
│      博亚和讯 | 新浪财经 | 大商所 | 中国饲料网 | Mock     │
└────────────────────────┬─────────────────────────────────┘
                         │ Database Write
┌────────────────────────▼─────────────────────────────────┐
│                   数据层 (Data Layer)                     │
│     PostgreSQL 16 + TimescaleDB + Redis 7                │
│        RAW表 | STANDARD表 | 时序优化 | 缓存加速          │
└──────────────────────────────────────────────────────────┘
```

### 技术栈详解

#### 1. 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Next.js** | 14.0.4 | React 全栈框架，提供 SSR/SSG |
| **React** | 18.2.0 | UI 组件库 |
| **TypeScript** | 5.3.3 | 类型安全的 JavaScript |
| **Tailwind CSS** | 3.4.0 | 实用优先的 CSS 框架 |
| **Radix UI** | 多个组件 | 无头 UI 组件（Dialog, Select, Switch 等） |
| **TanStack Query** | 5.104.5 | 数据获取和状态管理 |
| **ECharts** | 5.4.3 | 数据可视化图表库 |
| **Lucide Icons** | 0.303.0 | 现代化图标库 |
| **Zustand** | 4.4.7 | 轻量级状态管理 |
| **Axios** | 1.6.5 | HTTP 客户端 |

#### 2. 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Rust** | 1.83 | 高性能系统编程语言 |
| **Axum** | 0.7 | 异步 Web 框架 |
| **SeaORM** | 1.0 | 异步 ORM |
| **Tokio** | 1.x | 异步运行时 |
| **tokio-cron-scheduler** | 0.9 | Cron 任务调度器 |
| **Redis** | 0.24 | Redis 客户端 |
| **Serde** | 1.0 | 序列化/反序列化 |
| **Tracing** | 0.1 | 结构化日志 |

#### 3. 采集器技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.11+ | 采集器运行时 |
| **Requests** | 2.31+ | HTTP 请求库 |
| **BeautifulSoup4** | 4.12+ | HTML 解析 |
| **lxml** | 5.1+ | XML/HTML 高性能解析器 |
| **Pandas** | 2.2+ | 数据处理（可选） |

#### 4. 数据存储

| 技术 | 版本 | 用途 |
|------|------|------|
| **PostgreSQL** | 16 | 主数据库 |
| **TimescaleDB** | 2.14+ | 时序数据扩展 |
| **Redis** | 7 | 缓存和消息队列 |

### 数据流架构

```
┌─────────────────────────────────────────────────────────┐
│ 1. 任务触发                                              │
│    • Cron 定时任务（每日自动）                           │
│    • 手动触发（前端按钮）                                │
│    • API 调用                                           │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 2. Rust 后端处理                                         │
│    • 接收请求 (handlers.rs)                              │
│    • 验证参数                                            │
│    • 执行 Python 采集器 (python_bridge.rs)               │
│    • 创建异步任务 (async_jobs.rs)                        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 3. Python 采集器执行                                     │
│    • 加载采集器类 (run_collector.py)                     │
│    • 抓取网页数据 (collectors/*.py)                      │
│    • 解析 HTML/JSON                                     │
│    • 数据验证和清洗                                      │
│    • 输出 JSON 格式                                     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 4. 数据写入 RAW 层                                       │
│    • 插入 raw_corn_data 表                              │
│    • 保存原始数据                                        │
│    • 记录采集元数据                                      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 5. 数据标准化处理 (后台任务)                             │
│    • 读取 RAW 数据 (standardization.rs)                 │
│    • 数据转换和映射                                      │
│    • 质量评分（A/B/C/D）                                │
│    • 写入 standard_corn_data 表                         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 6. 实时通知                                              │
│    • Redis Pub/Sub (notification/)                      │
│    • 发布采集完成事件                                    │
│    • 前端接收更新通知                                    │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 7. 前端展示                                              │
│    • 自动刷新列表                                        │
│    • 更新统计卡片                                        │
│    • 显示最新数据                                        │
└─────────────────────────────────────────────────────────┘
```

### 核心模块说明

#### Backend-Rust 模块

```
backend-rust/src/
├── main.rs                     # 应用入口、路由配置
├── handlers.rs                 # 通用 API 处理器
├── collection_handlers.rs      # 采集相关 API
├── collection_execution.rs     # 采集执行逻辑
├── async_jobs.rs              # 异步任务管理
├── python_bridge.rs           # Python 桥接层
├── standardization.rs         # 数据标准化
├── errors.rs                  # 错误处理
├── models.rs                  # 数据模型
├── db/
│   ├── mod.rs                 # 数据库模块入口
│   ├── raw.rs                 # RAW 表操作
│   └── standard.rs            # STANDARD 表操作
├── scheduler/
│   ├── mod.rs                 # 调度器模块
│   └── cron.rs                # Cron 任务
└── notification/
    ├── mod.rs                 # 通知模块
    └── redis_pubsub.rs        # Redis 发布订阅
```

**关键文件说明**:

- `main.rs`: 初始化应用、配置路由、启动 HTTP 服务器
- `collection_execution.rs`: 核心采集逻辑，调用 Python 采集器
- `python_bridge.rs`: 通过命令行执行 Python 脚本，解析 JSON 输出
- `standardization.rs`: 数据质量评分和标准化转换

#### Frontend 模块

```
frontend/src/
├── app/
│   ├── layout.tsx             # 根布局
│   ├── page.tsx               # 首页
│   ├── collectors/
│   │   └── page.tsx           # 采集器管理页
│   ├── collection/
│   │   ├── page.tsx           # 数据采集列表
│   │   └── [id]/page.tsx      # 采集详情页
│   ├── scheduler/
│   │   └── page.tsx           # 任务调度页
│   ├── quality/
│   │   └── page.tsx           # 质量分析页
│   ├── monitor/
│   │   └── page.tsx           # 系统监控页
│   └── settings/
│       └── page.tsx           # 系统设置页
├── components/
│   ├── ui/                    # Radix UI 组件封装
│   ├── collectors/            # 采集器相关组件
│   ├── charts/                # 图表组件
│   └── layout/                # 布局组件
└── lib/
    ├── api.ts                 # API 客户端
    ├── types.ts               # TypeScript 类型定义
    └── utils.ts               # 工具函数
```

#### Collectors-Python 模块

```
collectors-python/
├── run_collector.py           # 统一入口（CLI）
├── config.py                  # 配置管理
├── collectors/
│   ├── base.py                # 采集器基类
│   ├── __init__.py            # 采集器注册
│   ├── mock.py                # Mock 采集器（测试用）
│   ├── sina.py                # 新浪财经
│   ├── sina_v2.py             # 新浪财经 V2
│   ├── sina_production.py     # 新浪财经（生产版）
│   ├── boyar.py               # 博亚和讯
│   ├── boyar_v2.py            # 博亚和讯 V2
│   ├── boyar_production.py    # 博亚和讯（生产版）
│   ├── dce.py                 # 大商所
│   ├── dce_production.py      # 大商所（生产版）
│   └── cft.py                 # 中国饲料网
└── tests/
    └── test_*.py              # 单元测试
```

**采集器基类接口**:

```python
class BaseCollector(ABC):
    @property
    @abstractmethod
    def collector_id(self) -> str:
        """采集器ID"""
        pass
    
    @abstractmethod
    def collect(self, max_items: Optional[int] = None) -> List[RawDataRecord]:
        """执行采集，返回原始数据记录列表"""
        pass
```

### 数据库架构

#### RAW 表 (`raw_corn_data`)

存储未处理的原始数据：

```sql
CREATE TABLE raw_corn_data (
    id BIGSERIAL PRIMARY KEY,
    business_date DATE NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ,
    
    data_type VARCHAR(50) NOT NULL,      -- arrivals/spot_price/inventory
    indicator VARCHAR(100) NOT NULL,     -- 指标名称
    value NUMERIC(15, 4) NOT NULL,       -- 数值
    unit VARCHAR(20) NOT NULL,           -- 单位
    region VARCHAR(100) NOT NULL,        -- 地区
    
    source_url TEXT,
    original_text TEXT,
    metadata JSONB,
    
    adapter_id VARCHAR(100) NOT NULL,    -- 采集器ID
    collection_run_id UUID
);

-- TimescaleDB 超表（时序优化）
SELECT create_hypertable('raw_corn_data', 'collected_at');
```

#### STANDARD 表 (`standard_corn_data`)

存储标准化后的数据：

```sql
CREATE TABLE standard_corn_data (
    id BIGSERIAL PRIMARY KEY,
    business_date DATE NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    indicator VARCHAR(100) NOT NULL,
    value NUMERIC(15, 4) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    region VARCHAR(100) NOT NULL,
    
    quality_grade CHAR(1) NOT NULL,      -- A/B/C/D
    quality_issues JSONB,
    
    source_adapter VARCHAR(100) NOT NULL,
    raw_data_id BIGINT REFERENCES raw_corn_data(id),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 时序优化
SELECT create_hypertable('standard_corn_data', 'business_date');
```

#### 采集管理表 (`collection_adapters`)

```sql
CREATE TABLE collection_adapters (
    id SERIAL PRIMARY KEY,
    adapter_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    adapter_type VARCHAR(50) NOT NULL,     -- python/rust
    command TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    config JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### API 规范

#### 基础 URL

```
开发环境: http://localhost:18000
生产环境: http://your-domain.com/api
```

#### 核心端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/adapters` | GET | 获取所有采集器 |
| `/api/adapters/:id/execute` | POST | 执行采集器 |
| `/api/raw-data` | GET | 获取原始数据 |
| `/api/standard-data` | GET | 获取标准数据 |
| `/api/collection-history` | GET | 获取采集历史 |
| `/api/async-jobs` | GET | 获取异步任务列表 |
| `/api/quality/summary` | GET | 获取质量统计 |

#### 请求示例

**执行采集器**:

```bash
curl -X POST http://localhost:18000/api/adapters/sina_production/execute \
  -H "Content-Type: application/json" \
  -d '{"max_items": 100}'
```

**响应**:

```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Collection job started",
  "adapter_id": "sina_production"
}
```

---

## 开发环境设置

### 前置要求

#### 系统要求

- **操作系统**: Linux / macOS / Windows (WSL2)
- **内存**: 至少 8GB RAM
- **磁盘**: 至少 20GB 可用空间

#### 必需软件

1. **Rust** (1.83+)
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   rustc --version
   ```

2. **Node.js** (18.x LTS)
   ```bash
   # 使用 nvm
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
   nvm install 18
   node --version
   ```

3. **Python** (3.11+)
   ```bash
   python3 --version
   pip3 install --upgrade pip
   ```

4. **PostgreSQL** (16+)
   ```bash
   # macOS
   brew install postgresql@16
   
   # Ubuntu
   sudo apt install postgresql-16
   ```

5. **Redis** (7+)
   ```bash
   # macOS
   brew install redis
   
   # Ubuntu
   sudo apt install redis-server
   ```

6. **Docker & Docker Compose** (推荐)
   ```bash
   docker --version
   docker-compose --version
   ```

### 快速启动（推荐）

使用 Docker Compose 一键启动所有服务：

```bash
# 1. 克隆项目
git clone <repository-url>
cd CornV2

# 2. 启动所有服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f

# 4. 访问系统
# 前端: http://localhost:3080
# 后端: http://localhost:18000
```

### 本地开发设置

#### 1. 数据库设置

```bash
# 启动 PostgreSQL
brew services start postgresql@16

# 创建数据库和用户
psql postgres
CREATE USER corn_user WITH PASSWORD 'corn_password_2026';
CREATE DATABASE corn_research OWNER corn_user;
\c corn_research
CREATE EXTENSION IF NOT EXISTS timescaledb;
\q

# 执行迁移
psql -U corn_user -d corn_research -f migrations/001_create_raw_table.sql
psql -U corn_user -d corn_research -f migrations/002_create_standard_table.sql
psql -U corn_user -d corn_research -f migrations/003_create_collection_management.sql
psql -U corn_user -d corn_research -f migrations/004_insert_test_adapters.sql
```

#### 2. Redis 设置

```bash
# 启动 Redis
brew services start redis

# 验证连接
redis-cli ping
# 应返回: PONG
```

#### 3. 后端设置

```bash
# 进入后端目录
cd backend-rust

# 复制环境变量
cp ../.env.example .env

# 编辑 .env
DATABASE_URL=postgresql://corn_user:corn_password_2026@localhost:5432/corn_research
REDIS_URL=redis://localhost:6379/0
RUST_LOG=debug

# 安装依赖并构建
cargo build

# 运行开发服务器
cargo run

# 或使用 watch 模式（自动重载）
cargo install cargo-watch
cargo watch -x run
```

#### 4. 前端设置

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 复制环境变量
echo "NEXT_PUBLIC_API_URL=http://localhost:18000" > .env.local

# 启动开发服务器
npm run dev

# 访问: http://localhost:3000
```

#### 5. Python 采集器设置

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r collectors-python/requirements.txt

# 测试采集器
python3 collectors-python/run_collector.py --collector mock --max-items 5
```

### 开发工具推荐

#### IDE 配置

**VS Code** (推荐):

```json
// .vscode/settings.json
{
  "rust-analyzer.checkOnSave.command": "clippy",
  "editor.formatOnSave": true,
  "[rust]": {
    "editor.defaultFormatter": "rust-lang.rust-analyzer"
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

推荐扩展：
- `rust-lang.rust-analyzer` - Rust 语言支持
- `dbaeumer.vscode-eslint` - ESLint
- `esbenp.prettier-vscode` - Prettier
- `ms-python.python` - Python 支持
- `bradlc.vscode-tailwindcss` - Tailwind CSS 智能提示

#### 调试配置

**Rust 后端调试**:

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "lldb",
      "request": "launch",
      "name": "Debug Backend",
      "cargo": {
        "args": ["build", "--bin=corn-backend"],
        "filter": {
          "name": "corn-backend",
          "kind": "bin"
        }
      },
      "args": [],
      "cwd": "${workspaceFolder}/backend-rust"
    }
  ]
}
```

---

## 开发指南

### 添加新采集器

#### 步骤 1: 创建采集器类

```bash
cd collectors-python/collectors
cp mock.py my_new_collector.py
```

#### 步骤 2: 实现采集器

```python
# my_new_collector.py
from typing import List, Optional
from collectors.base import BaseCollector, RawDataRecord
from datetime import datetime
import requests
from bs4 import BeautifulSoup

class MyNewCollector(BaseCollector):
    """我的新采集器"""
    
    @property
    def collector_id(self) -> str:
        return "my_new_collector"
    
    @property
    def site_name(self) -> str:
        return "我的数据源"
    
    @property
    def source_type(self) -> str:
        return "web"
    
    def collect(self, max_items: Optional[int] = None) -> List[RawDataRecord]:
        """执行采集"""
        records = []
        
        try:
            # 1. 发起 HTTP 请求
            url = "https://example.com/corn-data"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # 2. 解析 HTML
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 3. 提取数据
            for row in soup.select('table tr'):
                cols = row.find_all('td')
                if len(cols) < 4:
                    continue
                
                # 4. 创建记录
                record = RawDataRecord(
                    business_date=cols[0].text.strip(),
                    collected_at=datetime.now(),
                    published_at=None,
                    data_type="spot_price",
                    indicator="玉米现货价格",
                    value=float(cols[2].text.strip()),
                    unit="元/吨",
                    region=cols[1].text.strip(),
                    source_url=url,
                    original_text=row.text.strip(),
                    metadata={"source": "my_new_collector"}
                )
                records.append(record)
                
                if max_items and len(records) >= max_items:
                    break
        
        except Exception as e:
            print(f"采集失败: {e}", file=sys.stderr)
            return []
        
        return records
```

#### 步骤 3: 注册采集器

```python
# collectors/__init__.py
from .my_new_collector import MyNewCollector

COLLECTORS = {
    "my_new_collector": MyNewCollector,
    # ... 其他采集器
}
```

#### 步骤 4: 测试采集器

```bash
# 命令行测试
python3 collectors-python/run_collector.py --collector my_new_collector --max-items 10

# 单元测试
pytest collectors-python/tests/test_my_new_collector.py
```

#### 步骤 5: 添加到数据库

```sql
INSERT INTO collection_adapters (
    adapter_id, name, description, adapter_type, command, is_active
) VALUES (
    'my_new_collector',
    '我的数据源',
    '采集我的数据源的玉米数据',
    'python',
    'python3 /app/collectors-python/run_collector.py --collector my_new_collector',
    true
);
```

### 添加新 API 端点

#### 后端 (Rust)

```rust
// backend-rust/src/handlers.rs

use axum::{
    extract::{State, Path},
    response::Json,
};
use serde::{Deserialize, Serialize};

#[derive(Serialize)]
pub struct MyResponse {
    pub message: String,
    pub data: Vec<String>,
}

/// GET /api/my-endpoint/:id
pub async fn my_handler(
    State(pool): State<DatabaseConnection>,
    Path(id): Path<i32>,
) -> Result<Json<MyResponse>, AppError> {
    // 1. 查询数据库
    let results = my_table::Entity::find()
        .filter(my_table::Column::Id.eq(id))
        .all(&pool)
        .await?;
    
    // 2. 处理数据
    let data: Vec<String> = results
        .iter()
        .map(|r| r.name.clone())
        .collect();
    
    // 3. 返回响应
    Ok(Json(MyResponse {
        message: "Success".to_string(),
        data,
    }))
}
```

**注册路由**:

```rust
// backend-rust/src/main.rs

let app = Router::new()
    // ... 其他路由
    .route("/api/my-endpoint/:id", get(my_handler))
    .with_state(pool);
```

#### 前端 (TypeScript)

```typescript
// frontend/src/lib/api.ts

export interface MyResponse {
  message: string;
  data: string[];
}

export async function fetchMyData(id: number): Promise<MyResponse> {
  const response = await fetch(`${API_URL}/api/my-endpoint/${id}`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}
```

**在组件中使用**:

```typescript
// frontend/src/app/my-page/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { fetchMyData, type MyResponse } from '@/lib/api';

export default function MyPage() {
  const [data, setData] = useState<MyResponse | null>(null);
  
  useEffect(() => {
    fetchMyData(123)
      .then(setData)
      .catch(console.error);
  }, []);
  
  if (!data) return <div>Loading...</div>;
  
  return (
    <div>
      <h1>{data.message}</h1>
      <ul>
        {data.data.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
```

### 数据库迁移

#### 创建新迁移

```bash
# 创建迁移文件
touch migrations/006_add_new_column.sql
```

```sql
-- migrations/006_add_new_column.sql

-- 添加新列
ALTER TABLE standard_corn_data 
ADD COLUMN confidence_score NUMERIC(3, 2) DEFAULT 1.0;

-- 添加索引
CREATE INDEX idx_standard_corn_data_confidence 
ON standard_corn_data(confidence_score);

-- 添加注释
COMMENT ON COLUMN standard_corn_data.confidence_score IS '数据置信度 0.0-1.0';
```

#### 执行迁移

```bash
# 本地数据库
psql -U corn_user -d corn_research -f migrations/006_add_new_column.sql

# Docker 环境
docker exec -i corn_postgres psql -U corn_user -d corn_research < migrations/006_add_new_column.sql
```

#### 回滚迁移

```bash
# 创建回滚脚本
touch migrations/006_add_new_column_rollback.sql
```

```sql
-- 删除列
ALTER TABLE standard_corn_data DROP COLUMN confidence_score;

-- 删除索引
DROP INDEX IF EXISTS idx_standard_corn_data_confidence;
```

### 测试指南

#### 单元测试

**Rust 测试**:

```rust
// backend-rust/src/collection_execution_tests.rs

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_execute_collector() {
        let result = execute_python_collector(
            "mock",
            Some(5),
            None,
        ).await;
        
        assert!(result.is_ok());
        let records = result.unwrap();
        assert_eq!(records.len(), 5);
    }
}
```

运行测试：

```bash
cd backend-rust
cargo test
cargo test -- --nocapture  # 显示输出
```

**Python 测试**:

```python
# collectors-python/tests/test_mock.py

import pytest
from collectors.mock import MockCollector

def test_mock_collector():
    collector = MockCollector()
    records = collector.collect(max_items=10)
    
    assert len(records) == 10
    assert all(r.value > 0 for r in records)
    assert all(r.region in ["东北", "华北", "华东"] for r in records)

def test_mock_collector_with_limit():
    collector = MockCollector()
    records = collector.collect(max_items=3)
    
    assert len(records) == 3
```

运行测试：

```bash
cd collectors-python
pytest tests/
pytest tests/ -v  # 详细输出
pytest tests/test_mock.py::test_mock_collector  # 单个测试
```

#### 集成测试

```bash
# 运行端到端测试
cd tests/e2e
pytest test_data_pipeline.py
```

#### 性能测试

```bash
# 基准测试
cd tests/performance
python3 benchmark.py
```

### 日志和调试

#### Rust 日志

```rust
use tracing::{info, warn, error, debug};

// 不同级别的日志
debug!("调试信息: {:?}", data);
info!("信息: 采集器启动");
warn!("警告: 数据可能不完整");
error!("错误: 数据库连接失败: {}", err);
```

设置日志级别：

```bash
# 环境变量
export RUST_LOG=debug
cargo run

# 或在 .env 文件中
RUST_LOG=backend_rust=debug,tower_http=info
```

#### 前端调试

```typescript
// 开发环境调试
if (process.env.NODE_ENV === 'development') {
  console.log('API Response:', data);
}

// 使用 React DevTools
// Chrome 扩展: React Developer Tools
```

#### Python 日志

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.info("开始采集")
logger.error("采集失败", exc_info=True)
```

### 性能优化

#### 后端优化

1. **数据库连接池**:
```rust
// 调整连接池大小
let pool = Database::connect(
    ConnectOptions::new(database_url)
        .max_connections(20)
        .min_connections(5)
        .connect_timeout(Duration::from_secs(8))
).await?;
```

2. **异步并发**:
```rust
use tokio::task::JoinSet;

let mut set = JoinSet::new();
for adapter in adapters {
    set.spawn(execute_collector(adapter));
}

while let Some(result) = set.join_next().await {
    // 处理结果
}
```

3. **Redis 缓存**:
```rust
// 缓存查询结果
let cached: Option<String> = redis_conn
    .get(cache_key)
    .await?;

if let Some(data) = cached {
    return Ok(serde_json::from_str(&data)?);
}

// 查询数据库
let data = query_database().await?;

// 写入缓存
redis_conn
    .set_ex(cache_key, serde_json::to_string(&data)?, 3600)
    .await?;
```

#### 前端优化

1. **React Query 缓存**:
```typescript
export const useCollectors = () => {
  return useQuery({
    queryKey: ['collectors'],
    queryFn: fetchCollectors,
    staleTime: 5 * 60 * 1000,  // 5分钟内使用缓存
    refetchOnWindowFocus: false,
  });
};
```

2. **虚拟滚动**:
```typescript
import { useVirtualizer } from '@tanstack/react-virtual';

const virtualizer = useVirtualizer({
  count: items.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 50,
});
```

3. **代码分割**:
```typescript
import dynamic from 'next/dynamic';

const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <div>Loading...</div>,
  ssr: false,
});
```

---

## 贡献指南

### 贡献流程

我们欢迎所有形式的贡献！请遵循以下流程：

#### 1. Fork 项目

```bash
# 在 GitHub 上点击 Fork 按钮

# 克隆你的 Fork
git clone https://github.com/YOUR_USERNAME/CornV2.git
cd CornV2

# 添加上游仓库
git remote add upstream https://github.com/ORIGINAL_OWNER/CornV2.git
```

#### 2. 创建分支

```bash
# 创建功能分支
git checkout -b feature/my-new-feature

# 或修复分支
git checkout -b fix/bug-description
```

分支命名规范：
- `feature/xxx` - 新功能
- `fix/xxx` - Bug 修复
- `docs/xxx` - 文档更新
- `refactor/xxx` - 代码重构
- `test/xxx` - 测试相关
- `chore/xxx` - 构建/工具相关

#### 3. 开发和测试

```bash
# 进行代码更改

# 运行测试
cargo test           # Rust 测试
npm test            # 前端测试
pytest              # Python 测试

# 代码格式化
cargo fmt           # Rust
npm run lint        # 前端
black .             # Python
```

#### 4. 提交更改

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```bash
git add .
git commit -m "feat: 添加新的采集器支持"
```

提交消息格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type** 类型：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响代码运行）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具相关

示例：

```bash
git commit -m "feat(collectors): 添加中粮期货采集器

- 实现 COFCO 数据源采集
- 支持现货价格和到港量数据
- 添加单元测试

Closes #123"
```

#### 5. 推送分支

```bash
git push origin feature/my-new-feature
```

#### 6. 创建 Pull Request

1. 在 GitHub 上打开你的 Fork
2. 点击 "Compare & pull request"
3. 填写 PR 描述：

```markdown
## 变更说明
简要描述这个 PR 做了什么。

## 变更类型
- [ ] 新功能
- [ ] Bug 修复
- [ ] 文档更新
- [ ] 性能优化
- [ ] 其他

## 测试
说明如何测试这些变更。

## 截图（如适用）
添加截图帮助说明变更。

## 相关 Issue
Closes #123
```

4. 等待 Code Review

### 代码规范

#### Rust 代码规范

遵循 [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/)：

```rust
// ✅ 好的代码
pub async fn execute_collector(
    adapter_id: &str,
    max_items: Option<i32>,
) -> Result<Vec<RawDataRecord>, CollectionError> {
    let records = fetch_data(adapter_id, max_items).await?;
    validate_records(&records)?;
    Ok(records)
}

// ❌ 避免
pub async fn exec(id: &str, max: Option<i32>) -> Result<Vec<RawDataRecord>, Box<dyn Error>> {
    // ...
}
```

**命名规范**:
- 类型名: `PascalCase`
- 函数/变量: `snake_case`
- 常量: `SCREAMING_SNAKE_CASE`
- 生命周期: `'a`, `'b` (小写单字母)

#### TypeScript/React 代码规范

遵循 [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)：

```typescript
// ✅ 好的代码
interface CollectorData {
  id: number;
  name: string;
  isActive: boolean;
}

export function CollectorCard({ collector }: { collector: CollectorData }) {
  const [isLoading, setIsLoading] = useState(false);
  
  const handleExecute = async () => {
    setIsLoading(true);
    try {
      await executeCollector(collector.id);
    } catch (error) {
      console.error('Execution failed:', error);
    } finally {
      setIsLoading(false);
    }
  };
  
  return <div>{/* ... */}</div>;
}

// ❌ 避免
export function card(props: any) {
  const [loading, set_loading] = useState(false);
  // ...
}
```

**命名规范**:
- 组件: `PascalCase`
- 函数/变量: `camelCase`
- 常量: `UPPER_SNAKE_CASE`
- 类型/接口: `PascalCase`
- 文件名: `kebab-case.tsx`

#### Python 代码规范

遵循 [PEP 8](https://pep8.org/)：

```python
# ✅ 好的代码
from typing import List, Optional
from datetime import datetime

class CornCollector:
    """玉米数据采集器"""
    
    def __init__(self, source_url: str):
        self.source_url = source_url
        self._session = requests.Session()
    
    def collect_data(self, max_items: Optional[int] = None) -> List[dict]:
        """采集数据"""
        try:
            response = self._session.get(self.source_url)
            response.raise_for_status()
            return self._parse_response(response, max_items)
        except RequestException as e:
            logger.error(f"Failed to collect data: {e}")
            return []

# ❌ 避免
class collector:
    def __init__(self, url):
        self.url = url
    
    def getData(self, max):
        # ...
```

**命名规范**:
- 类名: `PascalCase`
- 函数/变量: `snake_case`
- 常量: `UPPER_SNAKE_CASE`
- 私有方法: `_leading_underscore`

### Code Review 检查清单

#### 功能性
- [ ] 代码实现了预期功能
- [ ] 所有测试通过
- [ ] 没有引入新的 Bug
- [ ] 边界情况已处理
- [ ] 错误处理完善

#### 代码质量
- [ ] 代码清晰易读
- [ ] 命名有意义
- [ ] 遵循项目代码规范
- [ ] 没有重复代码
- [ ] 复杂逻辑有注释

#### 性能
- [ ] 没有性能瓶颈
- [ ] 数据库查询优化
- [ ] 避免 N+1 查询
- [ ] 适当使用缓存

#### 安全性
- [ ] 输入验证
- [ ] SQL 注入防护
- [ ] XSS 防护
- [ ] 敏感数据处理

#### 文档
- [ ] 代码注释完整
- [ ] API 文档更新
- [ ] README 更新（如需要）
- [ ] CHANGELOG 更新

### 报告 Bug

使用 GitHub Issues 报告 Bug，请包含：

1. **问题描述**: 清晰简洁的描述
2. **复现步骤**: 详细的步骤
3. **预期行为**: 应该发生什么
4. **实际行为**: 实际发生了什么
5. **环境信息**:
   - OS: [e.g., macOS 13.0]
   - Rust version: [e.g., 1.83]
   - Node version: [e.g., 18.17.0]
   - Docker version: [e.g., 24.0.6]
6. **日志/截图**: 相关的错误日志或截图

### 功能请求

使用 GitHub Issues 提交功能请求，请包含：

1. **功能描述**: 你想要的功能
2. **使用场景**: 为什么需要这个功能
3. **建议实现**: 你的实现想法（可选）
4. **替代方案**: 其他可能的解决方案（可选）

---

## 附录

### 常用命令速查

#### Docker

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
docker-compose logs -f backend

# 重启服务
docker-compose restart
docker-compose restart backend

# 停止服务
docker-compose down

# 重新构建
docker-compose build
docker-compose build --no-cache backend

# 进入容器
docker exec -it corn_backend bash
docker exec -it corn_postgres psql -U corn_user -d corn_research

# 清理
docker-compose down -v  # 删除卷
docker system prune -a  # 清理所有未使用资源
```

#### Rust

```bash
# 编译
cargo build
cargo build --release

# 运行
cargo run
cargo run --release

# 测试
cargo test
cargo test -- --nocapture

# 格式化
cargo fmt
cargo fmt --check

# 代码检查
cargo clippy
cargo clippy -- -D warnings

# 文档
cargo doc --open

# 依赖更新
cargo update
```

#### Node/npm

```bash
# 安装依赖
npm install
npm ci  # 清洁安装

# 运行
npm run dev
npm run build
npm start

# 测试
npm test
npm run test:watch

# 代码检查
npm run lint
npm run lint:fix

# 类型检查
npm run type-check
```

#### Python

```bash
# 虚拟环境
python3 -m venv .venv
source .venv/bin/activate
deactivate

# 安装依赖
pip install -r requirements.txt
pip install -e .  # 开发模式

# 运行采集器
python3 collectors-python/run_collector.py --collector mock --max-items 10

# 测试
pytest
pytest -v
pytest tests/test_mock.py

# 代码格式化
black .
isort .

# 代码检查
flake8
mypy .
```

#### PostgreSQL

```bash
# 连接数据库
psql -U corn_user -d corn_research

# 执行 SQL 文件
psql -U corn_user -d corn_research -f migrations/001_create_raw_table.sql

# 导出数据
pg_dump -U corn_user corn_research > backup.sql

# 导入数据
psql -U corn_user -d corn_research < backup.sql

# 查看表
\dt
\d+ raw_corn_data

# 查看索引
\di
```

#### Redis

```bash
# 连接
redis-cli

# 基本命令
PING
SET key value
GET key
DEL key
KEYS *
FLUSHDB  # 清空当前库
```

### 环境变量参考

```bash
# .env 示例

# 数据库
DATABASE_URL=postgresql://corn_user:corn_password_2026@localhost:5432/corn_research
POSTGRES_USER=corn_user
POSTGRES_PASSWORD=corn_password_2026
POSTGRES_DB=corn_research

# Redis
REDIS_URL=redis://localhost:6379/0

# 后端
RUST_LOG=info  # trace, debug, info, warn, error
RUST_BACKTRACE=1
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# 前端
NEXT_PUBLIC_API_URL=http://localhost:18000
NODE_ENV=development  # development, production

# Python
PYTHONUNBUFFERED=1
PYTHONPATH=/app
```

### 故障排查

#### 常见问题

**1. 端口被占用**

```bash
# 查找占用端口的进程
lsof -i :18000
lsof -i :3080

# 杀死进程
kill -9 <PID>
```

**2. 数据库连接失败**

```bash
# 检查 PostgreSQL 状态
pg_isready -U corn_user

# 重启 PostgreSQL
brew services restart postgresql@16

# 检查连接
psql -U corn_user -d corn_research -c "SELECT 1"
```

**3. Redis 连接失败**

```bash
# 检查 Redis 状态
redis-cli ping

# 重启 Redis
brew services restart redis
```

**4. Rust 编译错误**

```bash
# 清理构建缓存
cargo clean

# 更新依赖
cargo update

# 重新构建
cargo build
```

**5. 前端构建失败**

```bash
# 删除 node_modules 和缓存
rm -rf node_modules .next

# 重新安装
npm install

# 重新构建
npm run build
```

**6. Docker 容器启动失败**

```bash
# 查看详细日志
docker-compose logs backend

# 重新构建镜像
docker-compose build --no-cache

# 检查配置
docker-compose config
```

### 资源链接

#### 官方文档

- [Rust Book](https://doc.rust-lang.org/book/)
- [Axum Documentation](https://docs.rs/axum/latest/axum/)
- [SeaORM Documentation](https://www.sea-ql.org/SeaORM/)
- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [TimescaleDB Documentation](https://docs.timescale.com/)

#### 学习资源

- [Rust by Example](https://doc.rust-lang.org/rust-by-example/)
- [Tokio Tutorial](https://tokio.rs/tokio/tutorial)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [Python Best Practices](https://docs.python-guide.org/)

#### 社区

- [Rust Users Forum](https://users.rust-lang.org/)
- [Next.js Discussions](https://github.com/vercel/next.js/discussions)
- [PostgreSQL Mailing Lists](https://www.postgresql.org/list/)

---

## 📞 获取帮助

如果你在开发过程中遇到问题：

1. **查看文档**: 首先查阅本指南和 README
2. **搜索 Issues**: 在 GitHub Issues 中搜索类似问题
3. **查看日志**: 检查应用日志寻找线索
4. **提问**: 在 GitHub Discussions 或 Issues 中提问
5. **联系维护者**: 通过 GitHub 联系项目维护者

---

**Happy Coding! 🎉**

最后更新: 2026-10-22  
维护者: Corn Research Team
