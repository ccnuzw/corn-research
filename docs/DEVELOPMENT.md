# 🚀 玉米研究系统 V2 - 开发文档

**版本**: v2.0.0  
**更新日期**: 2026-10-22

> 这是一份实践导向的开发文档，专注于快速上手和日常开发工作流。详细的技术参考请查看 [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)。

---

## 📖 目录

- [快速开始](#快速开始)
- [架构概览](#架构概览)
- [开发工作流](#开发工作流)
- [常见开发任务](#常见开发任务)
- [贡献指南](#贡献指南)
- [FAQ](#faq)

---

## 快速开始

### 5 分钟启动项目

```bash
# 1. 克隆项目
git clone <repository-url>
cd CornV2

# 2. 启动所有服务（推荐）
docker-compose up -d

# 3. 验证服务
curl http://localhost:18000/health
# 应返回: {"status":"ok"}

# 4. 访问前端
open http://localhost:3080
```

### 本地开发环境

如果你想在本地运行（不使用 Docker）：

```bash
# 启动数据库和 Redis
docker-compose up -d postgres redis

# 后端（终端 1）
cd backend-rust
export DATABASE_URL="postgresql://corn_user:corn_password_2026@localhost:15432/corn_research"
export REDIS_URL="redis://localhost:16380/0"
export RUST_LOG=debug
cargo run

# 前端（终端 2）
cd frontend
echo "NEXT_PUBLIC_API_URL=http://localhost:18000" > .env.local
npm install
npm run dev

# 访问: http://localhost:3000
```

---

## 架构概览

### 系统分层

```
┌─────────────────────────────────────┐
│  Frontend (Next.js + React)         │  ← 用户界面
├─────────────────────────────────────┤
│  API Gateway (Axum)                 │  ← REST API
├─────────────────────────────────────┤
│  Business Logic (Rust)              │  ← 业务处理
├─────────────────────────────────────┤
│  Collectors (Python)                │  ← 数据采集
├─────────────────────────────────────┤
│  Data Layer (PostgreSQL + Redis)    │  ← 数据存储
└─────────────────────────────────────┘
```

### 核心技术选型

| 层级 | 技术 | 原因 |
|------|------|------|
| **前端** | Next.js 14 + TypeScript | SSR、类型安全、开发效率 |
| **后端** | Rust + Axum | 高性能、内存安全、并发能力 |
| **采集器** | Python 3.11 | 灵活、生态丰富、易扩展 |
| **数据库** | PostgreSQL 16 + TimescaleDB | 成熟稳定、时序优化 |
| **缓存** | Redis 7 | 高性能、Pub/Sub 支持 |

### 数据流

```
用户触发 → Rust API → Python 采集器 → 抓取数据 
    ↓
写入 RAW 表 → 后台标准化 → 写入 STANDARD 表 
    ↓
Redis 通知 → 前端更新
```

### 项目结构

```
CornV2/
├── backend-rust/           # Rust 后端服务
│   ├── src/
│   │   ├── main.rs        # 入口 + 路由
│   │   ├── handlers.rs    # API 处理器
│   │   ├── collection_execution.rs  # 采集执行
│   │   ├── python_bridge.rs         # Python 桥接
│   │   └── db/            # 数据库操作
│   └── Cargo.toml
│
├── frontend/               # Next.js 前端
│   ├── src/
│   │   ├── app/           # 页面路由
│   │   ├── components/    # React 组件
│   │   └── lib/
│   │       ├── api.ts     # API 客户端
│   │       └── types.ts   # 类型定义
│   └── package.json
│
├── collectors-python/      # Python 采集器
│   ├── run_collector.py   # CLI 入口
│   ├── collectors/        # 采集器实现
│   │   ├── base.py        # 基类
│   │   ├── sina_production.py
│   │   ├── boyar_production.py
│   │   └── dce_production.py
│   └── requirements.txt
│
├── migrations/             # 数据库迁移
├── docker-compose.yml      # 容器编排
└── Dockerfile             # 后端镜像
```

---

## 开发工作流

### 日常开发流程

#### 1. 开始新功能

```bash
# 1. 拉取最新代码
git checkout main
git pull upstream main

# 2. 创建功能分支
git checkout -b feature/add-new-data-source

# 3. 启动开发环境
docker-compose up -d postgres redis
# 然后运行后端和前端（见上面的快速开始）
```

#### 2. 开发和测试

```bash
# 修改代码后...

# 后端: 自动重编译（使用 cargo-watch）
cargo install cargo-watch
cargo watch -x run

# 前端: 自动热重载（Next.js 内置）
npm run dev  # 已经在运行

# 运行测试
cargo test              # Rust 测试
npm test               # 前端测试
pytest                 # Python 测试
```

#### 3. 提交代码

```bash
# 格式化代码
cargo fmt              # Rust
npm run lint:fix       # 前端
black .                # Python

# 提交
git add .
git commit -m "feat: 添加新数据源支持"

# 推送
git push origin feature/add-new-data-source
```

#### 4. 创建 Pull Request

在 GitHub 上创建 PR，等待 Code Review。

### Git 工作流

我们使用 **Feature Branch Workflow**：

```
main (主分支，保护)
  ↓
feature/xxx (功能分支)
  ↓
Pull Request
  ↓
Code Review → 合并到 main
```

**分支命名**:
- `feature/xxx` - 新功能
- `fix/xxx` - Bug 修复
- `docs/xxx` - 文档
- `refactor/xxx` - 重构
- `test/xxx` - 测试

### 提交消息规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**常用 type**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 格式调整（不影响代码运行）
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

**示例**:

```bash
git commit -m "feat(collectors): 添加郑商所数据采集器"
git commit -m "fix(api): 修复日期查询边界问题"
git commit -m "docs: 更新 API 使用说明"
git commit -m "refactor(standardization): 优化质量评分算法"
```

---

## 常见开发任务

### 任务 1: 添加新采集器

**用时**: ~30 分钟

#### 步骤：

```bash
# 1. 创建采集器文件
cd collectors-python/collectors
cp sina_production.py my_source.py
```

#### 2. 实现采集器

```python
# my_source.py
from typing import List, Optional
from collectors.base import BaseCollector, RawDataRecord
from datetime import datetime
import requests
from bs4 import BeautifulSoup

class MySourceCollector(BaseCollector):
    @property
    def collector_id(self) -> str:
        return "my_source"
    
    @property
    def site_name(self) -> str:
        return "我的数据源"
    
    @property
    def source_type(self) -> str:
        return "web"
    
    def collect(self, max_items: Optional[int] = None) -> List[RawDataRecord]:
        records = []
        url = "https://example.com/corn-data"
        
        try:
            response = requests.get(url, timeout=30)
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 解析数据
            for row in soup.select('table tr')[:max_items]:
                record = RawDataRecord(
                    business_date="2024-01-01",
                    collected_at=datetime.now(),
                    published_at=None,
                    data_type="spot_price",
                    indicator="玉米现货价格",
                    value=2850.0,
                    unit="元/吨",
                    region="东北",
                    source_url=url,
                    original_text=row.text.strip(),
                    metadata={"source": self.collector_id}
                )
                records.append(record)
        except Exception as e:
            print(f"采集失败: {e}")
        
        return records
```

#### 3. 注册采集器

```python
# collectors/__init__.py
from .my_source import MySourceCollector

COLLECTORS = {
    "my_source": MySourceCollector,
    # ... 其他
}
```

#### 4. 测试

```bash
# 命令行测试
python3 collectors-python/run_collector.py --collector my_source --max-items 5

# 单元测试
pytest collectors-python/tests/test_my_source.py -v
```

#### 5. 添加到数据库

```sql
INSERT INTO collection_adapters (
    adapter_id, name, description, adapter_type, command, is_active
) VALUES (
    'my_source',
    '我的数据源',
    '采集我的数据源的玉米价格',
    'python',
    'python3 /app/collectors-python/run_collector.py --collector my_source',
    true
);
```

---

### 任务 2: 添加新 API 端点

**用时**: ~20 分钟

#### 后端实现

```rust
// backend-rust/src/handlers.rs

use axum::{
    extract::{State, Path, Query},
    response::Json,
};
use serde::{Deserialize, Serialize};

#[derive(Deserialize)]
pub struct QueryParams {
    pub start_date: Option<String>,
    pub end_date: Option<String>,
}

#[derive(Serialize)]
pub struct StatsResponse {
    pub total_records: i64,
    pub date_range: String,
    pub quality_summary: Vec<QualityCount>,
}

/// GET /api/stats/summary
pub async fn get_stats_summary(
    State(pool): State<DatabaseConnection>,
    Query(params): Query<QueryParams>,
) -> Result<Json<StatsResponse>, AppError> {
    // 查询逻辑
    let total = get_total_count(&pool, &params).await?;
    let quality = get_quality_counts(&pool, &params).await?;
    
    Ok(Json(StatsResponse {
        total_records: total,
        date_range: format!("{} to {}", 
            params.start_date.unwrap_or("N/A".to_string()),
            params.end_date.unwrap_or("N/A".to_string())
        ),
        quality_summary: quality,
    }))
}
```

#### 注册路由

```rust
// backend-rust/src/main.rs

let app = Router::new()
    // ... 其他路由
    .route("/api/stats/summary", get(get_stats_summary))
    .with_state(pool);
```

#### 前端调用

```typescript
// frontend/src/lib/api.ts

export interface StatsResponse {
  total_records: number;
  date_range: string;
  quality_summary: QualityCount[];
}

export async function fetchStatsSummary(
  startDate?: string,
  endDate?: string
): Promise<StatsResponse> {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  
  const response = await fetch(
    `${API_URL}/api/stats/summary?${params}`
  );
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}
```

#### 在组件中使用

```typescript
// frontend/src/app/stats/page.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchStatsSummary } from '@/lib/api';

export default function StatsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['stats', 'summary'],
    queryFn: () => fetchStatsSummary(),
  });
  
  if (isLoading) return <div>加载中...</div>;
  if (error) return <div>错误: {error.message}</div>;
  
  return (
    <div>
      <h1>统计概览</h1>
      <p>总记录数: {data?.total_records}</p>
      <p>日期范围: {data?.date_range}</p>
    </div>
  );
}
```

---

### 任务 3: 数据库迁移

**用时**: ~10 分钟

#### 创建迁移文件

```bash
# 创建新迁移
touch migrations/006_add_confidence_score.sql
```

#### 编写迁移 SQL

```sql
-- migrations/006_add_confidence_score.sql

-- 添加置信度字段
ALTER TABLE standard_corn_data 
ADD COLUMN confidence_score NUMERIC(3, 2) DEFAULT 1.0 
CHECK (confidence_score >= 0 AND confidence_score <= 1);

-- 添加索引
CREATE INDEX idx_standard_corn_data_confidence 
ON standard_corn_data(confidence_score) 
WHERE confidence_score < 0.8;

-- 添加注释
COMMENT ON COLUMN standard_corn_data.confidence_score 
IS '数据置信度分数，范围 0.0-1.0，默认 1.0';
```

#### 执行迁移

```bash
# Docker 环境
docker exec -i corn_postgres psql -U corn_user -d corn_research \
  < migrations/006_add_confidence_score.sql

# 本地环境
psql -U corn_user -d corn_research \
  -f migrations/006_add_confidence_score.sql
```

#### 验证

```bash
docker exec -it corn_postgres psql -U corn_user -d corn_research

corn_research=# \d+ standard_corn_data
# 应该看到新字段 confidence_score
```

---

### 任务 4: 添加前端页面

**用时**: ~30 分钟

#### 创建页面文件

```bash
cd frontend/src/app
mkdir analytics
touch analytics/page.tsx
```

#### 实现页面

```typescript
// frontend/src/app/analytics/page.tsx
'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchAnalytics } from '@/lib/api';

export default function AnalyticsPage() {
  const [dateRange, setDateRange] = useState('7d');
  
  const { data, isLoading } = useQuery({
    queryKey: ['analytics', dateRange],
    queryFn: () => fetchAnalytics(dateRange),
    refetchInterval: 30000, // 30秒刷新
  });
  
  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">数据分析</h1>
        
        <select 
          value={dateRange} 
          onChange={(e) => setDateRange(e.target.value)}
          className="px-4 py-2 border rounded"
        >
          <option value="7d">最近 7 天</option>
          <option value="30d">最近 30 天</option>
          <option value="90d">最近 90 天</option>
        </select>
      </div>
      
      {isLoading ? (
        <div className="text-center py-12">加载中...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <StatCard 
            title="总记录数" 
            value={data?.total_records} 
          />
          <StatCard 
            title="A级数据" 
            value={data?.a_grade_count} 
          />
          <StatCard 
            title="数据源" 
            value={data?.source_count} 
          />
        </div>
      )}
    </div>
  );
}

function StatCard({ title, value }: { title: string; value?: number }) {
  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-gray-500 text-sm">{title}</h3>
      <p className="text-3xl font-bold mt-2">
        {value?.toLocaleString() || '-'}
      </p>
    </div>
  );
}
```

#### 添加导航链接

```typescript
// frontend/src/components/layout/navbar.tsx

const navItems = [
  { href: '/', label: '首页' },
  { href: '/collectors', label: '采集器' },
  { href: '/collection', label: '数据采集' },
  { href: '/analytics', label: '数据分析' }, // 新增
  { href: '/scheduler', label: '任务调度' },
];
```

---

### 任务 5: 调试和日志

#### 查看日志

```bash
# Docker 日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs --tail=100

# 本地日志
# Rust 后端日志自动输出到 stdout
RUST_LOG=debug cargo run

# 前端开发服务器日志也输出到 stdout
npm run dev
```

#### 添加日志

**Rust**:

```rust
use tracing::{info, warn, error, debug};

pub async fn my_function() -> Result<()> {
    debug!("开始执行函数");
    info!("处理请求: adapter_id={}", adapter_id);
    
    match execute_task().await {
        Ok(result) => {
            info!("任务成功: {:?}", result);
            Ok(result)
        }
        Err(e) => {
            error!("任务失败: {}", e);
            Err(e)
        }
    }
}
```

**TypeScript**:

```typescript
// 开发环境日志
if (process.env.NODE_ENV === 'development') {
  console.log('API Response:', data);
  console.table(data.items);
}

// 生产环境错误日志
try {
  await fetchData();
} catch (error) {
  console.error('Failed to fetch data:', error);
  // 发送到监控服务
}
```

**Python**:

```python
import logging

logger = logging.getLogger(__name__)

def collect_data():
    logger.info("开始采集数据")
    try:
        data = fetch_data()
        logger.info(f"成功采集 {len(data)} 条记录")
        return data
    except Exception as e:
        logger.error(f"采集失败: {e}", exc_info=True)
        return []
```

---

## 贡献指南

### 如何贡献

我们欢迎各种形式的贡献：

- 🐛 **报告 Bug**
- 💡 **提出新功能建议**
- 📝 **改进文档**
- 🔧 **提交代码**

### 贡献流程

#### 1. Fork 项目

在 GitHub 上点击 Fork 按钮。

#### 2. 克隆你的 Fork

```bash
git clone https://github.com/YOUR_USERNAME/CornV2.git
cd CornV2
git remote add upstream https://github.com/ORIGINAL_OWNER/CornV2.git
```

#### 3. 创建分支

```bash
git checkout -b feature/my-awesome-feature
```

#### 4. 开发

按照上面的开发工作流进行开发。

#### 5. 提交

```bash
git add .
git commit -m "feat: 添加新功能"
git push origin feature/my-awesome-feature
```

#### 6. 创建 Pull Request

在 GitHub 上创建 PR，填写 PR 模板。

### 代码规范

#### Rust

```rust
// ✅ 好
pub async fn execute_collector(
    adapter_id: &str,
    max_items: Option<i32>,
) -> Result<Vec<Record>, Error> {
    let records = fetch_data(adapter_id, max_items).await?;
    Ok(records)
}

// ❌ 避免
pub async fn exec(id: &str, max: Option<i32>) -> Result<Vec<Record>, Box<dyn Error>> {
    // ...
}
```

**格式化**:

```bash
cargo fmt
cargo clippy
```

#### TypeScript

```typescript
// ✅ 好
interface CollectorData {
  id: number;
  name: string;
  isActive: boolean;
}

export async function fetchCollector(id: number): Promise<CollectorData> {
  const response = await fetch(`${API_URL}/api/collectors/${id}`);
  if (!response.ok) throw new Error('Failed to fetch');
  return response.json();
}

// ❌ 避免
export async function getCollector(id: any) {
  return fetch(`${API_URL}/api/collectors/${id}`).then(r => r.json());
}
```

**格式化**:

```bash
npm run lint
npm run lint:fix
```

#### Python

```python
# ✅ 好
from typing import List, Optional

def collect_data(
    source_url: str,
    max_items: Optional[int] = None
) -> List[dict]:
    """采集数据"""
    records = []
    # ...
    return records

# ❌ 避免
def getData(url, max=None):
    records = []
    # ...
    return records
```

**格式化**:

```bash
black .
isort .
flake8
```

### Pull Request 检查清单

提交 PR 前确保：

- [ ] 代码通过所有测试 (`cargo test`, `npm test`, `pytest`)
- [ ] 代码已格式化 (`cargo fmt`, `npm run lint:fix`, `black .`)
- [ ] 添加了必要的测试
- [ ] 更新了相关文档
- [ ] Commit 消息遵循规范
- [ ] PR 描述清晰完整

### 报告 Bug

使用 GitHub Issues，包含：

1. **问题描述**
2. **复现步骤**
3. **预期行为**
4. **实际行为**
5. **环境信息** (OS, Rust version, Node version, Docker version)
6. **日志/截图**

### 功能请求

使用 GitHub Issues，包含：

1. **功能描述**
2. **使用场景**
3. **建议实现**
4. **替代方案**

---

## FAQ

### Q1: Docker 容器无法启动怎么办？

```bash
# 查看详细日志
docker-compose logs backend

# 重新构建
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Q2: 端口被占用？

```bash
# 查找占用进程
lsof -i :18000
lsof -i :3080

# 修改端口（docker-compose.yml）
ports:
  - "28000:8000"  # 使用其他端口
```

### Q3: 数据库连接失败？

```bash
# 检查数据库状态
docker exec corn_postgres pg_isready -U corn_user

# 重启数据库
docker-compose restart postgres

# 验证连接
docker exec -it corn_postgres psql -U corn_user -d corn_research -c "SELECT 1"
```

### Q4: Rust 编译很慢？

```bash
# 使用 sccache 加速编译
cargo install sccache
export RUSTC_WRAPPER=sccache

# 或使用 mold 链接器（Linux）
sudo apt install mold
```

### Q5: 前端热重载不工作？

```bash
# 删除 .next 缓存
rm -rf frontend/.next

# 重启开发服务器
npm run dev
```

### Q6: Python 采集器找不到模块？

```bash
# 确保在正确的虚拟环境
source .venv/bin/activate

# 重新安装依赖
pip install -r collectors-python/requirements.txt

# 设置 PYTHONPATH
export PYTHONPATH=/path/to/CornV2:$PYTHONPATH
```

### Q7: 如何清理所有数据重新开始？

```bash
# ⚠️ 警告：这会删除所有数据
docker-compose down -v
docker-compose up -d
```

### Q8: 如何查看数据库内容？

```bash
# 进入 PostgreSQL
docker exec -it corn_postgres psql -U corn_user -d corn_research

# 常用查询
SELECT COUNT(*) FROM raw_corn_data;
SELECT COUNT(*) FROM standard_corn_data;
SELECT * FROM collection_adapters;
SELECT * FROM raw_corn_data ORDER BY collected_at DESC LIMIT 10;
```

### Q9: 如何手动触发采集？

```bash
# 方式 1: 通过 API
curl -X POST http://localhost:18000/api/adapters/sina_production/execute

# 方式 2: 直接运行 Python
docker exec corn_backend \
  python3 /app/collectors-python/run_collector.py \
  --collector sina_production \
  --max-items 100

# 方式 3: 前端界面
# 访问 http://localhost:3080/collectors
# 点击"立即运行"按钮
```

### Q10: 如何添加测试数据？

```bash
# 使用 Mock 采集器
docker exec corn_backend \
  python3 /app/collectors-python/run_collector.py \
  --collector mock \
  --max-items 1000

# 或执行 SQL
docker exec -i corn_postgres psql -U corn_user -d corn_research \
  < migrations/004_insert_test_adapters.sql
```

---

## 🔗 相关文档

- [README.md](../README.md) - 项目概览
- [DEPLOYMENT.md](../DEPLOYMENT.md) - 部署指南
- [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - 详细开发参考
- [API 文档](./API.md) - REST API 规范（待创建）

---

## 📞 获取帮助

- **文档**: 查看本文档和其他相关文档
- **Issues**: [GitHub Issues](https://github.com/OWNER/CornV2/issues)
- **讨论**: [GitHub Discussions](https://github.com/OWNER/CornV2/discussions)

---

**Happy Coding! 🚀**

最后更新: 2026-10-22  
维护者: Corn Research Team
