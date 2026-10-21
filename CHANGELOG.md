# 变更日志

本文档记录项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 计划新增
- FastAPI网关
- Next.js前端
- 完整的数据处理Pipeline

## [0.1.0] - 2026-10-20

### 新增
- 🎉 项目初始化
- ✅ Python采集器基础架构
  - BaseCollector抽象类
  - BoyarCollector（博亚和讯）完整实现
  - SinaCollector（新浪财经）框架
- ✅ Rust DDD核心
  - corn-domain领域层
    - Price实体
    - QualityScore值对象
    - Location值对象
  - corn-python PyO3绑定
- ✅ Python-Rust集成
  - calculate_quality_score() 函数
  - process_raw_data() 函数
  - 集成测试成功
- 📚 完整文档体系
  - DDD架构设计
  - 采集器设计规范
  - 混合技术栈说明
  - Git仓库管理
- 🐳 Docker基础设施配置
  - PostgreSQL + TimescaleDB
  - Redis

### 技术栈
- Python 3.11+
- Rust 2021 Edition
- FastAPI (计划)
- Next.js 14 (计划)
- PostgreSQL + TimescaleDB
- Redis

### 文档
- 23份完整技术文档
- README.md 项目说明
- README_PROGRESS.md 进度跟踪

### 提交
- 30个Git提交
- 21个源代码文件
- ~2000行代码

---

## 版本标签说明

- `v0.x.x` - 开发版本
- `v1.0.0-alpha` - Alpha测试版
- `v1.0.0-beta` - Beta测试版
- `v1.0.0` - 正式发布版

---

[Unreleased]: https://github.com/your-org/corn-research-v2/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-org/corn-research-v2/releases/tag/v0.1.0
