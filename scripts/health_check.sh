#!/bin/bash

# 健康检查脚本
# 用于监控系统运行状态

set -e

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

BACKEND_URL="${BACKEND_URL:-http://localhost:18000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3080}"

echo "=========================================="
echo "玉米研究系统 健康检查"
echo "=========================================="
echo ""

# 检查后端
echo -n "检查后端服务... "
if curl -f -s "${BACKEND_URL}/api/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
    BACKEND_OK=true
else
    echo -e "${RED}✗${NC}"
    BACKEND_OK=false
fi

# 检查前端
echo -n "检查前端服务... "
if curl -f -s "${FRONTEND_URL}" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
    FRONTEND_OK=true
else
    echo -e "${RED}✗${NC}"
    FRONTEND_OK=false
fi

# 检查数据库
echo -n "检查数据库连接... "
if docker-compose exec -T postgres pg_isready -U corn_user > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
    DB_OK=true
else
    echo -e "${RED}✗${NC}"
    DB_OK=false
fi

# 检查Redis
echo -n "检查Redis连接... "
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
    REDIS_OK=true
else
    echo -e "${RED}✗${NC}"
    REDIS_OK=false
fi

echo ""

# 如果所有服务正常，获取详细统计
if [ "$BACKEND_OK" = true ]; then
    echo "系统统计:"
    curl -s "${BACKEND_URL}/api/stats" | python3 -m json.tool 2>/dev/null || echo "无法获取统计信息"
    echo ""
fi

# 输出总结
echo "=========================================="
if [ "$BACKEND_OK" = true ] && [ "$FRONTEND_OK" = true ] && [ "$DB_OK" = true ] && [ "$REDIS_OK" = true ]; then
    echo -e "${GREEN}所有服务运行正常${NC}"
    exit 0
else
    echo -e "${RED}部分服务异常，请检查日志${NC}"
    exit 1
fi
