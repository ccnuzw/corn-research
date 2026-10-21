# 玉米研究系统V2 - Git仓库管理方案

**项目**: CornV2（全新项目，参考旧项目但独立开发）  
**目标**: 企业级标准的Git仓库管理

---

## 一、当前目录结构

```
CornV2/
├── .git/                          # Git仓库
├── .gitignore                     # Git忽略规则
├── .venv/                         # Python虚拟环境（已忽略）
│
├── collectors-python/             # Python采集器
│   ├── collectors/
│   │   ├── base.py
│   │   ├── boyar.py              # 博亚和讯
│   │   ├── sina.py               # 新浪财经
│   │   └── __init__.py
│   ├── requirements.txt
│   ├── tests/
│   └── README.md
│
├── core-rust/                     # Rust DDD核心
│   ├── Cargo.toml                # Workspace配置
│   ├── Cargo.lock
│   ├── corn-domain/              # 领域层
│   │   ├── src/
│   │   │   ├── market_data/
│   │   │   ├── collection/
│   │   │   └── lib.rs
│   │   └── Cargo.toml
│   ├── corn-python/              # PyO3绑定
│   │   ├── src/lib.rs
│   │   ├── Cargo.toml
│   │   └── pyproject.toml
│   └── target/                   # 编译产物（已忽略）
│
├── api-python/                    # FastAPI网关（待开发）
│   └── app/
│
├── frontend/                      # Next.js前端（待开发）
│
├── docs/                          # 文档
│   ├── ddd_architecture.md
│   ├── collector_design_specification.md
│   ├── correct_hybrid_architecture.md
│   ├── week1_day1_summary.md
│   └── ... (23份文档)
│
├── docker-compose.yml             # Docker配置
├── test_integration.py            # 集成测试
├── README.md
├── README_PROGRESS.md
├── COMPLETION.md
└── WEEK1_DAY1-2_COMPLETE.md
```

---

## 二、Git仓库管理建议

### 2.1 仓库基本信息

**仓库名称建议**:
- `corn-research-v2`
- `corn-market-data-platform`
- `corn-ddd-system`

**描述**:
```
企业级玉米市场研究与数据采集平台
Python采集器 + Rust DDD核心 + Next.js前端
```

**技术栈标签**:
- Python 3.11+
- Rust 2021
- FastAPI
- Next.js 14
- PostgreSQL + TimescaleDB
- DDD架构

### 2.2 完善的.gitignore

```gitignore
# Python
.venv/
venv/
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
*.coverage
.pytest_cache/

# Rust
target/
Cargo.lock  # 对于库保留，对于应用忽略
**/*.rs.bk
*.pdb

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Environment
.env
.env.local
.env.*.local
*.key
*.pem

# Next.js
.next/
out/
node_modules/
.npm/
*.tsbuildinfo

# Database
*.db
*.sqlite
*.sqlite3

# Logs
logs/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# OS
.DS_Store
Thumbs.db

# Temporary
tmp/
temp/
*.tmp
```

### 2.3 README.md 主文件结构

```markdown
# 玉米研究系统V2

> 企业级玉米市场研究与数据采集平台

## 架构

- **Python采集器**: 灵活快速的数据采集
- **Rust DDD核心**: 高性能业务逻辑
- **FastAPI网关**: RESTful API
- **Next.js前端**: 现代化Web界面

## 快速开始

### 前置要求
- Python 3.11+
- Rust 1.75+
- Node.js 18+
- Docker & Docker Compose

### 安装

```bash
# 克隆仓库
git clone https://github.com/your-org/corn-research-v2.git
cd corn-research-v2

# 启动基础设施
docker-compose up -d

# 安装Python依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r collectors-python/requirements.txt

# 编译Rust核心
cd core-rust/corn-python
maturin develop --release
cd ../..

# 运行测试
python test_integration.py
```

## 项目状态

- ✅ Week 1 Day 1-2: 基础架构完成
- 📝 Week 1 Day 3-7: 数据处理服务
- ⏳ Week 2: API网关开发

## 文档

- [DDD架构设计](docs/ddd_architecture.md)
- [采集器规范](docs/collector_design_specification.md)
- [开发进度](README_PROGRESS.md)

## License

Proprietary
```

---

## 三、Git分支策略

### 3.1 主分支

```
main            # 生产分支（稳定版本）
develop         # 开发主分支
```

### 3.2 功能分支命名

```
feature/week1-collectors     # 功能开发
feature/week2-api-gateway
feature/rust-dedup-service

fix/boyar-date-parsing       # Bug修复
fix/rust-compilation-error

docs/api-documentation       # 文档更新
docs/architecture-diagram

refactor/collector-base      # 重构
```

### 3.3 版本标签

```
v0.1.0-week1    # Week 1完成
v0.2.0-week2    # Week 2完成
v1.0.0-alpha    # Alpha版本
v1.0.0          # 正式发布
```

---

## 四、Commit规范

### 4.1 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 4.2 Type类型

```
feat:     新功能
fix:      修复Bug
docs:     文档更新
style:    代码格式（不影响功能）
refactor: 重构
perf:     性能优化
test:     测试
build:    构建系统
ci:       CI配置
chore:    其他杂项
```

### 4.3 示例

```bash
# 好的提交
feat(collectors): add BoyarCollector with HTML parsing
fix(rust-domain): correct import path in price.rs
docs(architecture): add DDD layer diagram

# 不好的提交
update code
fix bug
wip
```

---

## 五、目录结构优化建议

### 5.1 完整的项目结构

```
corn-research-v2/
├── .github/                       # GitHub配置
│   ├── workflows/                # CI/CD
│   │   ├── rust-test.yml
│   │   ├── python-test.yml
│   │   └── deploy.yml
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
│
├── collectors-python/             # Python采集器
│   ├── collectors/
│   ├── tests/
│   ├── requirements.txt
│   ├── requirements-dev.txt      # 开发依赖
│   ├── setup.py                  # 包配置
│   └── README.md
│
├── core-rust/                     # Rust DDD核心
│   ├── corn-domain/
│   ├── corn-application/         # 应用层（待开发）
│   ├── corn-infrastructure/      # 基础设施（待开发）
│   ├── corn-python/
│   ├── Cargo.toml
│   └── README.md
│
├── api-python/                    # FastAPI网关
│   ├── app/
│   ├── tests/
│   ├── requirements.txt
│   └── README.md
│
├── frontend/                      # Next.js前端
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── README.md
│
├── infrastructure/                # 基础设施配置
│   ├── docker/
│   │   ├── postgres/
│   │   ├── redis/
│   │   └── nginx/
│   ├── k8s/                      # Kubernetes（可选）
│   └── terraform/                # IaC（可选）
│
├── docs/                          # 文档
│   ├── architecture/
│   ├── api/
│   ├── deployment/
│   └── development/
│
├── scripts/                       # 工具脚本
│   ├── setup.sh
│   ├── test.sh
│   ├── deploy.sh
│   └── migrate.sh
│
├── tests/                         # 集成测试
│   ├── integration/
│   └── e2e/
│
├── .gitignore
├── .editorconfig                 # 编辑器配置
├── docker-compose.yml
├── docker-compose.dev.yml
├── Makefile                      # 便捷命令
├── README.md
├── LICENSE
└── CHANGELOG.md                  # 变更日志
```

---

## 六、Makefile便捷命令

```makefile
# Makefile
.PHONY: help setup test build clean

help:
	@echo "玉米研究系统V2 - 开发命令"
	@echo "setup    - 初始化开发环境"
	@echo "test     - 运行所有测试"
	@echo "build    - 编译Rust + Python"
	@echo "clean    - 清理编译产物"
	@echo "run      - 启动开发服务"

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r collectors-python/requirements.txt
	cd core-rust/corn-python && ../../.venv/bin/maturin develop --release

test:
	python test_integration.py
	cd core-rust && cargo test

build:
	cd core-rust && cargo build --release

clean:
	rm -rf .venv
	cd core-rust && cargo clean

run:
	docker-compose up -d
	cd api-python && uvicorn app.main:app --reload
```

---

## 七、CI/CD配置

### 7.1 GitHub Actions示例

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  rust-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
      - run: cd core-rust && cargo test

  python-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r collectors-python/requirements.txt
      - run: python test_integration.py
```

---

## 八、实施步骤

1. **立即优化.gitignore** ✅
2. **完善README.md** ✅
3. **添加Makefile** ✅
4. **创建develop分支**
5. **设置GitHub Actions**
6. **添加CHANGELOG.md**

---

**建议优先级**:
- P0: .gitignore, README.md
- P1: Makefile, 分支策略
- P2: CI/CD, CHANGELOG

准备好开始实施吗？
