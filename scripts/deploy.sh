#!/bin/bash

# 玉米研究系统V2 生产部署脚本
# 版本: 2.0.0
# 日期: 2026-10-21

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker和Docker Compose
check_dependencies() {
    log_info "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    log_info "依赖检查通过 ✓"
}

# 检查环境变量
check_env() {
    log_info "检查环境配置..."
    
    if [ ! -f .env.production ]; then
        log_error ".env.production 文件不存在"
        log_info "请从 .env.production.example 复制并配置"
        exit 1
    fi
    
    # 加载环境变量
    source .env.production
    
    # 检查关键配置
    if [ -z "$POSTGRES_PASSWORD" ]; then
        log_error "POSTGRES_PASSWORD 未设置"
        exit 1
    fi
    
    log_info "环境配置检查通过 ✓"
}

# 备份数据库
backup_database() {
    log_info "备份数据库..."
    
    BACKUP_DIR="./backups"
    mkdir -p "$BACKUP_DIR"
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/corn_research_${TIMESTAMP}.sql"
    
    if docker-compose ps postgres | grep -q "Up"; then
        docker-compose exec -T postgres pg_dump -U corn_user corn_research > "$BACKUP_FILE" 2>/dev/null || {
            log_warn "数据库备份失败（可能是首次部署）"
            return 0
        }
        
        # 压缩备份
        gzip "$BACKUP_FILE"
        log_info "数据库备份完成: ${BACKUP_FILE}.gz ✓"
        
        # 保留最近7天的备份
        find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete
    else
        log_warn "数据库未运行，跳过备份"
    fi
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."
    
    # 使用生产配置构建
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    log_info "镜像构建完成 ✓"
}

# 运行数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."
    
    # 等待数据库就绪
    log_info "等待数据库启动..."
    sleep 10
    
    # 执行迁移
    docker-compose -f docker-compose.prod.yml exec -T postgres psql -U corn_user -d corn_research < migrations/001_create_raw_table.sql || true
    docker-compose -f docker-compose.prod.yml exec -T postgres psql -U corn_user -d corn_research < migrations/002_create_standard_table.sql || true
    
    log_info "数据库迁移完成 ✓"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 使用生产配置启动
    docker-compose -f docker-compose.prod.yml up -d
    
    log_info "服务启动中..."
    
    # 等待服务就绪
    log_info "等待服务健康检查..."
    sleep 30
    
    # 检查服务状态
    docker-compose -f docker-compose.prod.yml ps
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    MAX_RETRIES=10
    RETRY_COUNT=0
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -f http://localhost:${BACKEND_PORT:-18000}/api/health &> /dev/null; then
            log_info "后端健康检查通过 ✓"
            return 0
        fi
        
        RETRY_COUNT=$((RETRY_COUNT + 1))
        log_warn "健康检查失败，重试 $RETRY_COUNT/$MAX_RETRIES..."
        sleep 5
    done
    
    log_error "健康检查失败，请检查日志"
    docker-compose -f docker-compose.prod.yml logs --tail=50 backend
    return 1
}

# 显示部署信息
show_info() {
    log_info "部署完成！"
    echo ""
    echo "=========================================="
    echo "玉米研究系统 V2.0.0"
    echo "=========================================="
    echo ""
    echo "访问地址:"
    echo "  前端: http://localhost:${FRONTEND_PORT:-3080}"
    echo "  后端API: http://localhost:${BACKEND_PORT:-18000}"
    echo "  API文档: http://localhost:${BACKEND_PORT:-18000}/docs"
    echo ""
    echo "数据库:"
    echo "  Host: localhost:${POSTGRES_PORT:-15432}"
    echo "  Database: ${POSTGRES_DB:-corn_research}"
    echo "  User: ${POSTGRES_USER:-corn_user}"
    echo ""
    echo "常用命令:"
    echo "  查看日志: docker-compose -f docker-compose.prod.yml logs -f"
    echo "  停止服务: docker-compose -f docker-compose.prod.yml down"
    echo "  重启服务: docker-compose -f docker-compose.prod.yml restart"
    echo "  查看状态: docker-compose -f docker-compose.prod.yml ps"
    echo ""
    echo "=========================================="
}

# 回滚函数
rollback() {
    log_error "部署失败，开始回滚..."
    
    docker-compose -f docker-compose.prod.yml down
    
    # 如果有备份，提示恢复
    LATEST_BACKUP=$(ls -t backups/*.sql.gz 2>/dev/null | head -1)
    if [ -n "$LATEST_BACKUP" ]; then
        log_info "可以从备份恢复: $LATEST_BACKUP"
        log_info "恢复命令: gunzip -c $LATEST_BACKUP | docker-compose exec -T postgres psql -U corn_user corn_research"
    fi
    
    exit 1
}

# 主函数
main() {
    log_info "开始部署玉米研究系统 V2.0.0..."
    echo ""
    
    # 设置错误处理
    trap rollback ERR
    
    # 执行部署步骤
    check_dependencies
    check_env
    backup_database
    build_images
    start_services
    run_migrations
    
    if health_check; then
        show_info
    else
        log_error "部署失败，请检查日志"
        exit 1
    fi
}

# 解析命令行参数
case "${1:-}" in
    --skip-backup)
        log_warn "跳过数据库备份"
        check_dependencies
        check_env
        build_images
        start_services
        run_migrations
        health_check && show_info
        ;;
    --no-build)
        log_info "跳过镜像构建"
        check_dependencies
        check_env
        backup_database
        start_services
        run_migrations
        health_check && show_info
        ;;
    --help)
        echo "用法: $0 [选项]"
        echo ""
        echo "选项:"
        echo "  --skip-backup    跳过数据库备份"
        echo "  --no-build       跳过镜像构建"
        echo "  --help           显示帮助信息"
        echo ""
        ;;
    *)
        main
        ;;
esac
