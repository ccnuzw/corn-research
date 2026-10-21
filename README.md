# 🌽 玉米研究系统 V2

**企业级玉米商品数据采集与分析平台**

[![Rust](https://img.shields.io/badge/Rust-1.83-orange.svg)](https://www.rust-lang.org/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue.svg)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-green.svg)](https://www.docker.com/)

---

## 📖 项目简介

玉米研究系统 V2 是一个**全栈数据采集与分析平台**，专注于玉米商品市场的数据收集、处理、质量管理和可视化展示。

### 核心特性

- 🚀 **高性能后端**: Rust + Axum + SeaORM
- 🎨 **现代化前端**: Next.js + React + TypeScript + Tailwind CSS
- 🐍 **灵活采集器**: Python 动态加载，支持多数据源
- 📊 **时序数据库**: PostgreSQL + TimescaleDB
- 🔄 **实时通知**: Redis Pub/Sub
- 🎯 **任务调度**: Cron 表达式定时任务
- 📈 **数据质量**: 四级质量评分（A/B/C/D）
- 🐳 **容器化部署**: Docker + Docker Compose

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────┐
│         Next.js Frontend (React/TS)         │
│  采集器管理 | 数据监控 | 任务调度 | 质量分析 │
└─────────────────┬───────────────────────────┘
                  │ HTTP REST API
┌─────────────────▼───────────────────────────┐
│         Rust Backend (Axum + SeaORM)        │
│  API服务 | 异步任务 | 通知服务 | 数据转换  │
└─────────────────┬───────────────────────────┘
                  │ Command Line + JSON
┌─────────────────▼───────────────────────────┐
│       Python Collectors (动态加载)          │
│  博亚和讯 | 新浪财经 | 大商所 | 中国饲料网  │
└─────────────────┬───────────────────────────┘
                  │ Write
┌─────────────────▼───────────────────────────┐
│   PostgreSQL + TimescaleDB + Redis          │
│  RAW层 | STANDARD层 | 采集管理 | 缓存      │
└─────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ 可用内存

### 一键启动

```bash
# 克隆项目
git clone <repository-url>
cd CornV2

# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 访问系统

- 🌐 **前端界面**: http://localhost:3080
- 🔌 **后端 API**: http://localhost:18000
- ✅ **健康检查**: http://localhost:18000/health

---

## 📦 功能模块

### 1. 采集器管理 (`/collectors`)

- ✅ 查看所有采集器状态
- ✅ 手动运行采集任务
- ✅ 启动/停止采集器
- ✅ 查看运行历史
- ✅ 批量操作

### 2. 数据采集监控 (`/collection`)

- ✅ 实时数据展示
- ✅ 统计卡片（总记录数、A级数据、数据天数）
- ✅ 最近采集记录
- ✅ 自动刷新（10秒）

### 3. 定时任务管理 (`/scheduler`)

- ✅ Cron 表达式配置
- ✅ 任务启用/禁用
- ✅ 下次运行时间显示
- ✅ 手动触发执行

### 4. 数据质量分析 (`/quality`)

- ✅ 质量评分分布（A/B/C/D）
- ✅ 质量问题列表
- ✅ 问题详情和受影响记录
- ✅ 质量规则说明

### 5. 系统监控 (`/monitor`)

- ✅ CPU/内存/磁盘/网络监控
- ✅ 服务状态实时显示
- ✅ 实时日志查看
- ✅ 数据库连接池状态
- ✅ Redis 状态监控

### 6. 系统设置 (`/settings`)

- ✅ 通知设置
- ✅ 数据库配置
- ✅ 安全设置（API密钥、IP白名单）
- ✅ 性能优化
- ✅ 界面主题

---

## 🛠️ 技术栈

### 后端
- **Rust 1.83**: 高性能、内存安全
- **Axum**: 异步 Web 框架
- **SeaORM**: 现代化 ORM
- **tokio**: 异步运行时
- **tokio-cron-scheduler**: 任务调度

### 前端
- **Next.js 15**: React 全栈框架
- **TypeScript**: 类型安全
- **Tailwind CSS**: 实用优先的 CSS
- **Radix UI**: 无头 UI 组件
- **Lucide Icons**: 现代图标库

### 数据采集
- **Python 3.11**: 采集器运行时
- **requests**: HTTP 客户端
- **BeautifulSoup4**: HTML 解析
- **lxml**: XML/HTML 处理

### 数据存储
- **PostgreSQL 16**: 主数据库
- **TimescaleDB**: 时序扩展
- **Redis 7**: 缓存和消息队列

---

## 📊 数据流程

```
1. 定时任务触发 / 手动触发
         ↓
2. Rust 后端调用 Python 采集器
         ↓
3. 采集器抓取网页数据
         ↓
4. 数据写入 RAW 表（原始数据）
         ↓
5. 后台标准化处理
         ↓
6. 数据写入 STANDARD 表（标准数据）
         ↓
7. 质量评分和异常检测
         ↓
8. Redis 发布实时通知
         ↓
9. 前端接收更新并展示
```

---

## 🔧 开发指南

### 本地开发

**后端开发**:
```bash
cd backend-rust
cargo run
```

**前端开发**:
```bash
cd frontend
npm install
npm run dev
```

**添加新采集器**:
```bash
# 1. 创建采集器类
cp collectors-python/collectors/mock_collector.py collectors-python/collectors/my_collector.py

# 2. 实现 collect() 方法
# 3. 在 run_collector.py 中注册

# 4. 测试
python3 collectors-python/run_collector.py --collector my_collector
```

### 项目结构

```
CornV2/
├── backend-rust/           # Rust 后端
│   ├── src/
│   │   ├── main.rs        # 入口
│   │   ├── handlers/      # API 处理器
│   │   ├── db/            # 数据库模型
│   │   └── services/      # 业务逻辑
│   └── Cargo.toml
├── frontend/               # Next.js 前端
│   ├── src/
│   │   ├── app/           # 页面
│   │   ├── components/    # 组件
│   │   └── lib/           # 工具库
│   └── package.json
├── collectors-python/      # Python 采集器
│   ├── collectors/        # 采集器实现
│   ├── run_collector.py   # 统一入口
│   └── requirements.txt
├── migrations/             # SQL 迁移脚本
├── docker-compose.yml      # Docker 编排
├── Dockerfile             # 后端镜像
└── frontend.Dockerfile    # 前端镜像
```

---

## 📚 文档

- [部署指南](DEPLOYMENT.md) - 完整的部署说明
- [开发报告](FINAL_REPORT.md) - 项目开发总结
- [API 文档](docs/api.md) - REST API 规范（即将推出）

---

## 🎯 路线图

### v2.0 (当前版本) ✅
- [x] 核心架构搭建
- [x] 6 个主要前端页面
- [x] 完整的后端 API
- [x] 10+ Python 采集器
- [x] Docker 容器化部署

### v2.1 (计划中)
- [ ] WebSocket 实时推送
- [ ] 用户认证和权限管理
- [ ] 数据导出功能
- [ ] 图表可视化增强
- [ ] 性能优化

### v2.2 (规划中)
- [ ] 移动端适配
- [ ] 国际化支持
- [ ] 机器学习预测
- [ ] 自动化报告生成

---

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

---

## 👨‍💻 作者

**Corn Research Team**

- 项目主页: [GitHub Repository]
- 问题反馈: [GitHub Issues]

---

## 🌟 致谢

感谢以下开源项目：

- [Rust](https://www.rust-lang.org/)
- [Next.js](https://nextjs.org/)
- [PostgreSQL](https://www.postgresql.org/)
- [TimescaleDB](https://www.timescale.com/)
- [Redis](https://redis.io/)

---

**⭐ 如果这个项目对你有帮助，请给一个 Star！**

**最后更新**: 2026-10-21  
**版本**: v2.0.0  
**完成度**: 95%
