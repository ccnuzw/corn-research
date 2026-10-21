# 架构设计文档

**版本**: v2.0.0-release  
**日期**: 2026-10-21  

## 概述

玉米研究系统V2采用现代化微服务架构，将数据采集、存储、处理和展示解耦，确保系统的可扩展性、可维护性和高性能。

## 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                           用户层                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Web UI   │  │ Mobile   │  │ API CLI  │  │ 第三方    │       │
│  │ (Next.js)│  │ (未来)   │  │          │  │ 集成      │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API网关层                                │
│  ┌──────────────────────────────────────────────────────┐       │
│  │         Rust Backend (Axum + SeaORM)                 │       │
│  │  - RESTful API (20+ endpoints)                       │       │
│  │  - 请求验证与路由                                     │       │
│  │  - CORS & 安全中间件                                 │       │
│  │  - 响应缓存                                          │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
┌───────────────────┐ ┌──────────────┐ ┌──────────────────┐
│  业务逻辑层        │ │  缓存层       │ │  采集器层         │
│                   │ │              │ │                  │
│ StandardizationSvc│ │  Redis       │ │  Python Collectors│
│ QualityAssessment │ │  - 数据缓存  │ │  - boyar_prod    │
│ LineageTracker    │ │  - Pub/Sub   │ │  - sina_prod     │
│ DataTransformer   │ │  - 游标管理  │ │  - 限速/重试      │
└───────────────────┘ └──────────────┘ │  - HTML存档       │
            │                           └──────────────────┘
            ▼                                   │
┌─────────────────────────────────────────────────────────────────┐
│                         数据持久层                               │
│  ┌───────────────────────────┐  ┌──────────────────────────┐   │
│  │   PostgreSQL 16           │  │   文件系统                │   │
│  │                           │  │                          │   │
│  │  RAW层 (原始数据)         │  │  HTML存档 (gzip)         │   │
│  │  - raw_collection_records │  │  - data/raw/html/        │   │
│  │  - 完整性约束             │  │  - 按日期/来源组织        │   │
│  │  - 去重索引               │  │                          │   │
│  │                           │  └──────────────────────────┘   │
│  │  STANDARD层 (标准化数据)  │                                 │
│  │  - market_facts_standard  │                                 │
│  │  - 质量评分               │                                 │
│  │  - 数据血统               │                                 │
│  │  - 版本管理               │                                 │
│  └───────────────────────────┘                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. 前端层 (Next.js 14)

**技术栈**:
- Next.js 14 App Router
- TypeScript 5.0+
- Tailwind CSS 3
- Apache ECharts
- Shadcn/ui组件库

**职责**:
- 用户界面渲染（SSR + CSR）
- API调用与状态管理
- 数据可视化（图表、仪表盘）
- 主题切换（深色/浅色）
- 响应式布局

**目录结构**:
```
frontend/
├── src/
│   ├── app/              # 页面路由
│   │   ├── page.tsx      # 首页
│   │   ├── dashboard/    # 仪表盘
│   │   ├── collectors/   # 采集器管理
│   │   ├── data/         # 数据查询
│   │   ├── quality/      # 质量监控
│   │   └── settings/     # 系统设置
│   ├── components/       # UI组件
│   │   ├── ui/           # Shadcn组件
│   │   ├── charts/       # 图表组件
│   │   └── layout/       # 布局组件
│   └── lib/              # 工具库
│       ├── api.ts        # API客户端
│       └── utils.ts      # 工具函数
└── package.json
```

### 2. 后端层 (Rust + Axum)

**技术栈**:
- Rust 1.80+
- Axum Web框架
- SeaORM (ORM)
- Tokio (异步运行时)
- Tower (中间件)

**职责**:
- RESTful API服务
- 业务逻辑处理
- 数据标准化转换
- 质量评估算法
- 缓存管理
- 数据血统追溯

**目录结构**:
```
backend-rust/
├── src/
│   ├── main.rs           # 入口文件
│   ├── handlers/         # API处理器
│   │   ├── collectors.rs
│   │   ├── data.rs
│   │   ├── quality.rs
│   │   └── lineage.rs
│   ├── services/         # 业务服务
│   │   ├── standardization.rs
│   │   ├── quality_assessment.rs
│   │   └── cache.rs
│   ├── models/           # 数据模型
│   │   ├── raw_record.rs
│   │   └── standard_record.rs
│   └── utils/            # 工具函数
└── Cargo.toml
```

### 3. 采集器层 (Python 3.11)

**技术栈**:
- Python 3.11+
- aiohttp (异步HTTP)
- BeautifulSoup4 (HTML解析)
- redis-py (Redis客户端)

**职责**:
- 多源数据采集
- 增量采集（游标管理）
- 限速与重试
- HTML原始数据存档
- 数据清洗与预处理

**采集器列表**:
1. **博亚和讯采集器** (`boyar_production.py`)
   - 采集玉米现货价格
   - 市场分析文章
   - 增量采集支持

2. **新浪财经采集器** (`sina_production.py`)
   - 期货行情数据
   - 多数据源策略
   - Mock兜底机制

**采集流程**:
```
开始 → 检查游标 → 构建请求 → 限速等待 → 发送请求
   ↓
解析响应 → 数据清洗 → 保存HTML → 写入RAW层 → 更新游标
   ↓
重试机制（失败时） → 结束
```

### 4. 数据层

#### PostgreSQL 16

**表结构**:

**RAW层** (`raw_collection_records`):
```sql
CREATE TABLE raw_collection_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collector_id VARCHAR(50) NOT NULL,
    source_url TEXT NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_content JSONB NOT NULL,
    content_hash VARCHAR(64) UNIQUE NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_collector_id ON raw_collection_records(collector_id);
CREATE INDEX idx_collected_at ON raw_collection_records(collected_at DESC);
CREATE UNIQUE INDEX idx_content_hash ON raw_collection_records(content_hash);
```

**STANDARD层** (`market_facts_standard`):
```sql
CREATE TABLE market_facts_standard (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_date DATE NOT NULL,
    indicator_name VARCHAR(100) NOT NULL,
    value NUMERIC(18,4) NOT NULL,
    unit VARCHAR(20),
    region VARCHAR(50),
    
    -- 质量评分
    quality_grade CHAR(1) CHECK (quality_grade IN ('A','B','C','D')),
    quality_score NUMERIC(5,2),
    quality_issues JSONB,
    
    -- 数据血统
    source_id VARCHAR(50) NOT NULL,
    raw_record_id UUID REFERENCES raw_collection_records(id),
    
    -- 时间戳
    collected_at TIMESTAMPTZ NOT NULL,
    standardized_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 版本管理
    version INT DEFAULT 1,
    is_latest BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_business_date ON market_facts_standard(business_date DESC);
CREATE INDEX idx_indicator ON market_facts_standard(indicator_name);
CREATE INDEX idx_quality_grade ON market_facts_standard(quality_grade);
CREATE INDEX idx_is_latest ON market_facts_standard(is_latest);
```

**视图**:
```sql
-- 只返回最新版本
CREATE VIEW market_facts_standard_latest AS
SELECT * FROM market_facts_standard WHERE is_latest = TRUE;

-- 只返回高质量数据（A/B级）
CREATE VIEW market_facts_standard_quality AS
SELECT * FROM market_facts_standard 
WHERE quality_grade IN ('A', 'B') AND is_latest = TRUE;
```

#### Redis 7

**用途**:
1. **数据缓存**: API响应缓存，TTL 5分钟
2. **Pub/Sub**: 实时通知（采集完成、质量告警）
3. **游标管理**: 采集器增量采集位置

**键命名规范**:
```
cache:api:{endpoint}:{params_hash}     # API缓存
collector:cursor:{collector_id}        # 采集器游标
collector:status:{collector_id}        # 采集器状态
quality:alert:{record_id}              # 质量告警
```

### 5. 文件存储

**HTML存档**:
```
data/raw/html/
├── boyar/
│   ├── 2026-10-21/
│   │   ├── 001.html.gz
│   │   ├── 002.html.gz
│   │   └── ...
│   └── 2026-10-22/
└── sina/
    └── 2026-10-21/
```

**特点**:
- gzip压缩存储（节省70%+空间）
- 按日期和来源组织
- 支持原始数据追溯

## 数据流

### 采集流程

```
┌──────────┐
│  数据源  │
└─────┬────┘
      │ HTTP请求
      ▼
┌──────────────┐
│ Python采集器 │
│  - 限速       │
│  - 重试       │
│  - 解析       │
└──────┬───────┘
       │
       ├──→ data/raw/html/ (HTML存档)
       │
       ▼
┌──────────────┐
│  RAW层       │
│ PostgreSQL   │
└──────┬───────┘
       │ 触发转换
       ▼
┌──────────────┐
│ 标准化服务    │
│  - 清洗       │
│  - 格式化     │
│  - 质量评估   │
└──────┬───────┘
       │ B级以上
       ▼
┌──────────────┐
│ STANDARD层   │
│ PostgreSQL   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Redis缓存   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  前端展示    │
└──────────────┘
```

### 查询流程

```
用户请求 → API网关 → 检查缓存
                       │
                       ├─ 命中 → 返回缓存数据
                       │
                       └─ 未命中 → 查询数据库
                                    │
                                    ▼
                                 应用业务逻辑
                                    │
                                    ▼
                                 写入缓存
                                    │
                                    ▼
                                 返回结果
```

## 质量评估算法

### 评分维度

1. **来源可信度 (60%)**
   ```rust
   match source {
       "官方" => 100.0,
       "交易所" => 95.0,
       "商业数据" => 85.0,
       "公开媒体" => 75.0,
       _ => 60.0
   }
   ```

2. **数据完整性 (20%)**
   - 必填字段完整性
   - 元数据丰富度
   - 原文引用

3. **合理性检查 (15%)**
   ```rust
   // 业务规则示例
   if indicator == "山东玉米到车量" {
       if value < 100.0 || value > 2000.0 {
           issues.push("数值超出合理范围");
           score -= 15.0;
       }
   }
   ```

4. **时效性 (5%)**
   ```rust
   let age_hours = (now - collected_at).hours();
   if age_hours > 72 {
       score -= 5.0;
   }
   ```

### 等级划分

| 等级 | 分数范围 | 说明 | 自动晋升 |
|------|----------|------|----------|
| A | 90-100 | 优秀，官方来源，完整准确 | ✅ |
| B | 80-89 | 良好，商业来源，基本完整 | ✅ |
| C | 70-79 | 及格，媒体来源，部分缺失 | ❌ |
| D | <70 | 不合格，数据存在问题 | ❌ |

## 缓存策略

### 缓存层级

1. **API响应缓存**
   - TTL: 5分钟
   - 键模式: `cache:api:{endpoint}:{params_hash}`
   - 适用: GET请求

2. **查询结果缓存**
   - TTL: 10分钟
   - 键模式: `cache:query:{query_hash}`
   - 适用: 复杂查询

3. **静态数据缓存**
   - TTL: 1小时
   - 键模式: `cache:static:{resource}`
   - 适用: 指标列表、配置

### 缓存失效策略

- **主动失效**: 数据更新时清除相关缓存
- **被动失效**: TTL到期自动清除
- **全局清除**: 管理员手动触发

## 安全考虑

### 当前版本

1. **输入验证**: 所有API参数严格验证
2. **SQL注入防护**: 使用SeaORM参数化查询
3. **CORS配置**: 限制允许的源
4. **错误处理**: 不暴露内部实现细节

### 未来版本

1. **认证**: JWT Token + API Key
2. **授权**: 基于角色的访问控制 (RBAC)
3. **审计日志**: 记录所有敏感操作
4. **速率限制**: 防止API滥用
5. **HTTPS**: 强制使用加密连接

## 性能优化

### 数据库优化

1. **索引策略**:
   - 主键: UUID with B-tree
   - 时间字段: DESC索引（常用降序查询）
   - 联合索引: (business_date, indicator_name)

2. **查询优化**:
   - 避免 SELECT *
   - 使用 LIMIT + OFFSET 分页
   - 利用视图简化复杂查询

3. **连接池**:
   - 最小连接数: 5
   - 最大连接数: 20
   - 空闲超时: 10分钟

### API优化

1. **响应缓存**: Redis缓存热点数据
2. **异步处理**: Tokio异步运行时
3. **连接复用**: HTTP/1.1 Keep-Alive
4. **数据压缩**: gzip响应体

### 前端优化

1. **代码分割**: Next.js动态导入
2. **图片优化**: Next.js Image组件
3. **SSR**: 关键页面服务端渲染
4. **CDN**: 静态资源CDN加速（未来）

## 可扩展性

### 水平扩展

1. **无状态API**: 支持多实例负载均衡
2. **数据库读写分离**: 主从复制（未来）
3. **缓存集群**: Redis Cluster（未来）

### 垂直扩展

1. **数据库**: 增加CPU/内存
2. **Redis**: 增加内存
3. **应用服务器**: 增加CPU核心数

### 功能扩展

1. **新采集器**: 实现 `BaseCollector` 接口
2. **新API端点**: 添加新的handler
3. **新数据源**: 扩展STANDARD表字段

## 监控与日志

### 日志级别

- **ERROR**: 系统错误，需立即处理
- **WARN**: 警告信息，需关注
- **INFO**: 一般信息，运行状态
- **DEBUG**: 调试信息，开发使用

### 监控指标

1. **系统指标**:
   - CPU使用率
   - 内存使用率
   - 磁盘I/O

2. **应用指标**:
   - API响应时间 (P50, P95, P99)
   - 请求QPS
   - 错误率

3. **业务指标**:
   - 采集成功率
   - 数据质量分布
   - 缓存命中率

## 部署架构

### Docker Compose部署

```yaml
services:
  postgres:
    image: postgres:16
    ports: [15432:5432]
    volumes: [./data/postgres:/var/lib/postgresql/data]
  
  redis:
    image: redis:7-alpine
    ports: [16380:6379]
  
  backend:
    build: .
    ports: [18000:18000]
    depends_on: [postgres, redis]
  
  frontend:
    build: ./frontend
    ports: [3080:3000]
    depends_on: [backend]
```

### 生产部署（未来）

```
┌─────────────┐
│   Nginx     │ (反向代理 + SSL)
└──────┬──────┘
       │
       ├─→ Frontend (Next.js) × 2
       │
       └─→ Backend (Rust) × 3
              │
              ├─→ PostgreSQL (主) + 从库
              │
              └─→ Redis Cluster
```

## 技术决策记录

### ADR-001: 选择Rust作为后端语言

**决策**: 使用Rust替代Python作为主后端语言

**理由**:
- 高性能: 接近C++的性能
- 内存安全: 无GC，零成本抽象
- 并发安全: 编译时检查数据竞争
- 生态成熟: Axum + SeaORM + Tokio

**权衡**: 学习曲线较陡，开发速度较Python慢

### ADR-002: 采用两层数据存储 (RAW + STANDARD)

**决策**: 原始数据和标准化数据分层存储

**理由**:
- 数据溯源: 保留原始数据完整性
- 灵活性: 可重新标准化
- 质量控制: 在转换过程中评估

**权衡**: 存储空间增加约50%

### ADR-003: 使用Redis作为缓存

**决策**: Redis而非Memcached

**理由**:
- 数据结构丰富: String, Hash, List, Set
- 持久化支持: RDB + AOF
- Pub/Sub功能: 实时通知
- 游标管理: 支持复杂数据类型

**权衡**: 内存消耗略高

---

**维护者**: 玉米研究团队  
**最后更新**: 2026-10-21
