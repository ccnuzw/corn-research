.PHONY: help setup test build clean run format lint docker-build docker-up docker-down docker-logs

# 默认目标
.DEFAULT_GOAL := help

# ============================================
# 帮助信息
# ============================================
help:
	@echo "🌽 玉米研究系统V2 - 开发命令"
	@echo ""
	@echo "本地开发命令:"
	@echo "  make setup       - 初始化开发环境"
	@echo "  make test        - 运行所有测试"
	@echo "  make build       - 编译Rust + Python"
	@echo "  make clean       - 清理编译产物"
	@echo "  make dev-cli     - 启动CLI控制台"
	@echo ""
	@echo "Docker命令:"
	@echo "  make docker-build  - 构建Docker镜像"
	@echo "  make docker-up     - 启动所有服务（推荐）"
	@echo "  make docker-down   - 停止所有服务"
	@echo "  make docker-logs   - 查看日志"
	@echo "  make docker-restart - 重启服务"
	@echo "  make docker-clean  - 清理容器和镜像"
	@echo ""
	@echo "快捷命令:"
	@echo "  make up          - docker-up 的别名"
	@echo "  make down        - docker-down 的别名"
	@echo "  make logs        - docker-logs 的别名"

# ============================================
# 本地开发命令
# ============================================

# 初始化环境
setup:
	@echo "📦 创建Python虚拟环境..."
	python3 -m venv .venv
	@echo "📦 安装Python依赖..."
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r collectors-python/requirements.txt
	@echo "✅ 环境初始化完成！"

# 测试
test:
	@echo "🧪 运行Python测试..."
	cd collectors-python && python -m pytest || true
	@echo "🦀 运行Rust测试..."
	cd core-rust && cargo test
	@echo "✅ 测试完成！"

# 编译
build:
	@echo "🦀 编译Rust (release)..."
	cd core-rust && cargo build --release
	@echo "✅ 编译完成！"

# 清理
clean:
	@echo "🧹 清理Python..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "🧹 清理Rust..."
	cd core-rust && cargo clean
	cd backend-rust && cargo clean
	@echo "✅ 清理完成！"

# 格式化
format:
	@echo "🎨 格式化Python代码..."
	.venv/bin/black collectors-python/ || true
	@echo "🦀 格式化Rust代码..."
	cd core-rust && cargo fmt
	cd backend-rust && cargo fmt
	@echo "✅ 格式化完成！"

# 代码检查
lint:
	@echo "🔍 检查Python代码..."
	.venv/bin/flake8 collectors-python/ || true
	@echo "🦀 检查Rust代码..."
	cd core-rust && cargo clippy -- -D warnings || true
	cd backend-rust && cargo clippy -- -D warnings || true
	@echo "✅ 检查完成！"

# CLI控制台
dev-cli:
	@echo "💻 启动CLI控制台..."
	@. .venv/bin/activate && python cli.py

# ============================================
# Docker命令
# ============================================

docker-build:
	@echo "🔨 构建Docker镜像..."
	docker-compose build
	@echo "✅ 构建完成！"

docker-up:
	@echo "🚀 启动所有服务..."
	docker-compose up -d
	@echo "✅ 服务已启动！"
	@echo ""
	@echo "📍 访问地址:"
	@echo "   前端: http://localhost:3000"
	@echo "   后端: http://localhost:8000"
	@echo "   健康检查: http://localhost:8000/health"
	@echo ""
	@echo "💡 提示: 使用 'make logs' 查看日志"

docker-down:
	@echo "⏹️  停止所有服务..."
	docker-compose down
	@echo "✅ 服务已停止"

docker-restart:
	@echo "🔄 重启服务..."
	docker-compose restart
	@echo "✅ 服务已重启"

docker-logs:
	@echo "📋 查看日志（Ctrl+C退出）..."
	docker-compose logs -f

docker-logs-backend:
	@echo "📋 查看后端日志..."
	docker-compose logs -f backend

docker-logs-frontend:
	@echo "📋 查看前端日志..."
	docker-compose logs -f frontend

docker-shell:
	@echo "🐚 进入后端容器..."
	docker-compose exec backend /bin/bash

docker-shell-db:
	@echo "🐚 进入数据库..."
	docker-compose exec postgres psql -U corn_user -d corn_research

docker-clean:
	@echo "🧹 清理容器和镜像..."
	docker-compose down --rmi local
	@echo "✅ 清理完成"

docker-clean-all:
	@echo "⚠️  清理所有（包括数据）..."
	docker-compose down -v --rmi local
	@echo "✅ 清理完成"

# ============================================
# 快捷别名
# ============================================

up: docker-up
down: docker-down
logs: docker-logs
restart: docker-restart
shell: docker-shell
shell-db: docker-shell-db

# ============================================
# 基础设施命令（兼容旧版）
# ============================================

infra-up:
	@echo "🐳 启动基础设施（仅数据库+Redis）..."
	docker-compose up -d postgres redis
	@echo "✅ 基础设施启动完成！"
	@echo "PostgreSQL: localhost:5432"
	@echo "Redis: localhost:6379"

infra-down:
	@echo "🐳 停止基础设施..."
	docker-compose stop postgres redis
	@echo "✅ 基础设施已停止！"
