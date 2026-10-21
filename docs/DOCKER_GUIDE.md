# 🐳 Docker部署指南

## 快速启动（3步）

### 1. 确认Docker已安装
```bash
docker --version
docker-compose --version
```

如果未安装，从 https://www.docker.com/products/docker-desktop/ 下载Docker Desktop

### 2. 构建并启动
```bash
cd /Users/apple/CornV2

# 一键启动（首次会自动构建）
make up
```

### 3. 访问服务
- **前端**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/health

---

## 常用命令

### 服务管理
```bash
make up          # 启动所有服务
make down        # 停止所有服务
make restart     # 重启服务
make logs        # 查看所有日志
make logs-backend  # 仅后端日志
```

### 开发调试
```bash
make shell       # 进入后端容器
make shell-db    # 进入数据库
make test        # 运行测试
```

### 清理
```bash
make clean       # 清理容器（保留数据）
make clean-all   # 清理所有（危险！）
```

---

## 架构说明

### 服务列表
- **backend** (port 8000) - Rust Axum + PyO3采集器
- **frontend** (port 3000) - Next.js 14
- **postgres** (port 5432) - TimescaleDB
- **redis** (port 6379) - 缓存

### 数据持久化
- PostgreSQL数据 → `/var/lib/docker/volumes/cornv2_postgres-data`
- Redis数据 → `/var/lib/docker/volumes/cornv2_redis-data`
- 应用数据 → `./data/`

---

## 常见问题

### Q1: 端口冲突
**错误**: `port is already allocated`

**解决**:
```bash
# 检查占用
lsof -i :3000
lsof -i :8000

# 修改docker-compose.yml端口映射
ports:
  - "3001:3000"  # 改用3001
```

### Q2: 构建失败
**错误**: `failed to build`

**解决**:
```bash
# 清理缓存重新构建
docker-compose build --no-cache
```

### Q3: PyO3链接错误
**Docker中不会出现！** Docker使用标准Linux Python，无macOS链接问题

### Q4: 数据库连接失败
**错误**: `connection refused`

**解决**:
```bash
# 等待数据库启动（健康检查需要10-30秒）
make logs-backend

# 手动检查数据库
make shell-db
```

---

## 本地开发（不用Docker）

如果想在macOS上本地开发：

```bash
# CLI方式（推荐，无PyO3问题）
make dev-cli

# 或分别启动
make dev-backend    # Rust后端（会遇到PyO3问题）
make dev-frontend   # Next.js前端
```

**建议**: 本地用CLI开发调试，Docker运行完整系统

---

## 性能优化

### 加速构建
```bash
# 使用BuildKit
export DOCKER_BUILDKIT=1
docker-compose build
```

### 资源限制
```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

---

## 生产部署

### 环境变量
创建 `.env` 文件：
```bash
DATABASE_URL=postgresql://user:pass@host:5432/db
RUST_LOG=warn
```

### SSL/HTTPS
建议使用Nginx反向代理：
```nginx
server {
    listen 443 ssl;
    server_name corn.example.com;
    
    location / {
        proxy_pass http://localhost:3000;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
    }
}
```

---

## 监控

### 查看容器状态
```bash
docker-compose ps
docker stats
```

### 健康检查
```bash
curl http://localhost:8000/health
```

---

**刀哥，Docker配置已完成！运行`make up`立即启动！** 🚀
