# 玉米研究系统 V2

**版本**: 2.0.0-release  
**启动日期**: 2026-10-20  
**状态**: 生产就绪

## 项目简介

玉米研究系统V2是一个企业级大宗商品研究管理平台，专注于玉米市场数据的采集、质量评估、标准化存储和可视化分析。系统采用现代化技术栈，提供完整的数据血统追溯和多维度质量评估能力。

## 核心特性

- 🎨 **现代化UI**: 深色主题设计，参考Kiro.rs风格，响应式布局
- 📊 **智能数据采集**: 多源采集器，增量采集，限速重试，HTML存档
- 🔍 **质量评估体系**: A/B/C/D四级评分，多维度质量检测
- 🏗️ **企业级架构**: Rust后端 + Next.js前端 + PostgreSQL + Redis
- 🔬 **完整血统追溯**: RAW → STANDARD 全链路追踪
- 📈 **可视化分析**: ECharts图表，实时监控仪表盘

## 技术栈

### 后端
- **Rust 1.80+**: Axum框架 + SeaORM + Tokio异步运行时
- **PostgreSQL 16**: 主数据库，支持JSONB和全文搜索
- **Redis 7**: 缓存 + Pub/Sub + 游标管理
- **Python 3.11**: 采集器实现，PyO3集成

### 前端
- **Next.js 14**: App Router，服务端渲染
- **TypeScript 5.0+**: 类型安全
- **Tailwind CSS 3**: 实用优先的CSS框架
- **Apache ECharts**: 数据可视化
- **Shadcn/ui**: UI组件库

### 部署
- **Docker & Docker Compose**: 容器化部署
- **Nginx**: 反向代理
- **多阶段构建**: 优化镜像体积

## 快速开始

### 使用Docker Compose（推荐）

```bash
# 克隆仓库
cd /Users/apple/CornV2

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 访问应用
# 前端: http://localhost:3080
# 后端API: http://localhost:18000
# API文档: http://localhost:18000/docs
```

### 本地开发

#### 1. 前置要求
- Node.js 18+
- Rust 1.80+
- Python 3.11+
- PostgreSQL 16+
- Redis 7+

#### 2. 数据库初始化

```bash
# 启动PostgreSQL和Redis
docker-compose up -d postgres redis

# 运行迁移
./scripts/migrate_db.sh
```

#### 3. 启动后端

```bash
cd backend-rust
cargo build --release
cargo run --release

# 后端运行在 http://localhost:18000
```

#### 4. 启动前端

```bash
cd frontend
npm install
npm run dev

# 前端运行在 http://localhost:3080
```

#### 5. 运行采集器

```bash
# 安装Python依赖
cd collectors-python
pip install -r requirements.txt

# 运行博亚采集器
python -m collectors.boyar_production

# 运行新浪采集器
python -m collectors.sina_production
```

## 项目结构

```
CornV2/
├── backend-rust/          # Rust后端服务
│   ├── src/
│   │   ├── main.rs       # 入口文件
│   │   ├── handlers/     # API处理器
│   │   ├── models/       # 数据模型
│   │   ├── services/     # 业务逻辑
│   │   └── utils/        # 工具函数
│   └── Cargo.toml
├── frontend/              # Next.js前端
│   ├── src/
│   │   ├── app/          # 页面路由
│   │   ├── components/   # UI组件
│   │   └── lib/          # 工具库
│   └── package.json
├── collectors-python/     # Python采集器
│   └── collectors/
│       ├── boyar_production.py
│       └── sina_production.py
├── migrations/            # 数据库迁移
│   ├── 001_create_raw_table.sql
│   └── 002_create_standard_table.sql
├── tests/                 # 测试套件
│   ├── e2e/              # 端到端测试
│   ├── integration/      # 集成测试
│   └── performance/      # 性能测试
├── scripts/               # 运维脚本
│   ├── migrate_db.sh
│   └── deploy.sh
├── docs/                  # 文档
│   ├── API.md
│   ├── ARCHITECTURE.md
│   ├── USER_GUIDE.md
│   └── DEVELOPER.md
├── docker-compose.yml
├── Dockerfile
└── README.md
```

## 核心功能

### 1. 数据采集
- **博亚和讯**: 玉米现货价格、市场分析文章
- **新浪财经**: 期货行情、市场动态
- **增量采集**: Redis游标管理，避免重复
- **限速重试**: 1.5秒间隔，3次重试，指数退避
- **HTML存档**: gzip压缩存储，完整保留原始数据

### 2. 质量评估
- **来源可信度（60%）**: 官方(100) > 交易所(95) > 商业(85) > 媒体(75)
- **数据完整性（20%）**: 必填字段检查
- **合理性检查（15%）**: 业务规则验证
- **时效性（5%）**: 超过72小时扣分

### 3. 数据标准化
- **RAW层**: 原始数据，完整保留
- **STANDARD层**: 标准化格式，质量评分
- **自动晋升**: B级以上自动晋升
- **版本管理**: 支持数据更新和历史查询

### 4. 血统追溯
- 完整的数据流向追踪
- 从STANDARD记录追溯到RAW记录
- 显示采集器、URL、采集时间

### 5. 数据查询
- 多维度查询（日期、指标、地区、来源）
- 分页、排序、过滤
- 缓存优化，响应时间<200ms

### 6. 监控与告警
- 实时采集进度监控
- 质量评分仪表盘
- 缓存命中率统计
- 系统健康检查

## API端点

详细API文档见 [docs/API.md](docs/API.md)

### 核心端点
- `GET /api/health` - 健康检查
- `GET /api/collectors` - 列出采集器
- `POST /api/collectors/run` - 运行采集器
- `GET /api/data/raw` - 查询RAW层数据
- `GET /api/data/standard` - 查询STANDARD层数据
- `GET /api/data/:id/lineage` - 查询数据血统
- `GET /api/quality/summary` - 质量汇总
- `GET /api/cache/stats` - 缓存统计

## 测试

```bash
# 运行所有测试
cd tests

# 端到端测试
python e2e/test_collectors.py
python e2e/test_data_pipeline.py
python e2e/test_frontend.py

# 集成测试
python integration/test_api.py

# 性能测试
python performance/benchmark.py
```

## 部署

### 生产环境部署

```bash
# 使用生产配置
docker-compose -f docker-compose.prod.yml up -d

# 或使用部署脚本
./scripts/deploy.sh
```

### 环境变量

创建 `.env` 文件：

```env
# 数据库
DATABASE_URL=postgresql://corn_user:corn_pass@localhost:15432/corn_research

# Redis
REDIS_URL=redis://localhost:16380

# 后端
BACKEND_PORT=18000
RUST_LOG=info

# 前端
NEXT_PUBLIC_API_URL=http://localhost:18000
```

## 性能指标

- **API响应时间**: <200ms (P95)
- **缓存命中率**: >80%
- **并发处理**: 支持100并发用户
- **数据库查询**: <100ms (常见查询)
- **采集速率**: 1条/1.5秒（限速保护）

## 开发指南

详细开发文档见 [docs/DEVELOPER.md](docs/DEVELOPER.md)

### 添加新采集器

```python
# collectors-python/collectors/my_collector.py
from .base import BaseCollector

class MyCollector(BaseCollector):
    def collect(self, max_items=100):
        # 实现采集逻辑
        pass
```

### 添加新API端点

```rust
// backend-rust/src/handlers/my_handler.rs
use axum::{Json, response::IntoResponse};

pub async fn my_handler() -> impl IntoResponse {
    Json(json!({"status": "ok"}))
}
```

## 故障排查

### 常见问题

1. **数据库连接失败**
   ```bash
   # 检查PostgreSQL是否运行
   docker-compose ps postgres
   
   # 查看日志
   docker-compose logs postgres
   ```

2. **Redis连接失败**
   ```bash
   # 检查Redis是否运行
   docker-compose ps redis
   
   # 测试连接
   redis-cli -p 16380 ping
   ```

3. **前端无法连接后端**
   ```bash
   # 检查后端是否运行
   curl http://localhost:18000/api/health
   
   # 检查CORS配置
   # 查看 backend-rust/src/main.rs 中的CORS设置
   ```

更多问题见 [docs/USER_GUIDE.md#故障排查](docs/USER_GUIDE.md)

## 贡献指南

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 版本历史

- **v2.0.0-release** (2026-10-21) - 生产就绪版本
  - ✅ 完整的测试覆盖（>80%）
  - ✅ 生产级采集器（限速、重试、断点续传）
  - ✅ 完整的数据血统追溯
  - ✅ 质量评估体系（A/B/C/D）
  - ✅ Docker部署优化
  - ✅ 完整文档

- **v2.0.0-alpha** (2026-10-20) - 初始版本
  - 基础架构搭建
  - 核心功能实现

## 许可证

Private Project - All Rights Reserved

## 联系方式

- 项目维护者: 玉米研究团队
- 问题反馈: 通过GitHub Issues

## 致谢

- [Kiro.rs](https://kiro.rs) - UI设计灵感
- [Rust](https://www.rust-lang.org/) - 系统编程语言
- [Next.js](https://nextjs.org/) - React框架
- [PostgreSQL](https://www.postgresql.org/) - 数据库
- [Redis](https://redis.io/) - 缓存服务

---

**Happy Coding! 🌽**
