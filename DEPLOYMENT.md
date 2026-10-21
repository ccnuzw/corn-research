# 玉米研究系统 V2 - 部署指南

## 📋 系统要求

### 硬件要求
- **CPU**: 2核心以上
- **内存**: 4GB 以上（推荐 8GB）
- **磁盘**: 20GB 以上可用空间
- **网络**: 稳定的互联网连接

### 软件要求
- **Docker**: 20.10+ 
- **Docker Compose**: 2.0+
- **操作系统**: Linux / macOS / Windows (with WSL2)

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd CornV2
```

### 2. 构建镜像

```bash
# 构建所有服务
docker-compose build

# 或分别构建
docker-compose build backend
docker-compose build frontend
```

### 3. 启动服务

```bash
# 启动所有服务（后台运行）
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 4. 验证部署

```bash
# 检查服务状态
docker-compose ps

# 应该看到所有服务都是 healthy 状态
```

### 5. 访问系统

- **前端界面**: http://localhost:3080
- **后端 API**: http://localhost:18000
- **健康检查**: http://localhost:18000/health

---

## 🔧 服务配置

### 端口映射

| 服务 | 容器端口 | 主机端口 | 说明 |
|------|---------|---------|------|
| Frontend | 3000 | 3080 | Next.js 前端 |
| Backend | 8000 | 18000 | Rust API 服务 |
| PostgreSQL | 5432 | 15432 | 数据库 |
| Redis | 6379 | 16380 | 缓存服务 |

### 环境变量

在 `docker-compose.yml` 中可以修改以下环境变量：

**Backend**
```yaml
RUST_LOG: info                    # 日志级别: trace, debug, info, warn, error
DATABASE_URL: postgresql://...    # 数据库连接
REDIS_URL: redis://...           # Redis 连接
```

**Frontend**
```yaml
NEXT_PUBLIC_API_URL: http://backend:8000  # API 地址
```

**PostgreSQL**
```yaml
POSTGRES_USER: corn_user
POSTGRES_PASSWORD: corn_pass_2024
POSTGRES_DB: corn_research
```

---

## 📊 数据库初始化

### 自动初始化

首次启动时会自动执行：
```bash
# TimescaleDB 扩展
CREATE EXTENSION IF NOT EXISTS timescaledb;

# 执行迁移脚本
/migrations/*.sql
```

### 手动初始化

如需重新初始化数据库：

```bash
# 停止服务
docker-compose down

# 删除数据卷
docker volume rm cornv2_postgres_data

# 重新启动
docker-compose up -d
```

### 插入测试数据

```bash
# 执行测试数据脚本
docker exec corn_postgres psql -U corn_user -d corn_research -f /docker-entrypoint-initdb.d/004_insert_test_adapters.sql
```

---

## 🔍 故障排查

### 后端无法启动

**问题**: `GLIBC version not found`

**解决**: 
```bash
# 重新构建后端镜像
docker-compose build --no-cache backend
docker-compose up -d backend
```

**问题**: `exec format error`

**原因**: 二进制文件架构不匹配（如 macOS ARM64 vs Linux x86_64）

**解决**: 必须在 Docker 容器内编译
```bash
# 使用多阶段构建确保正确编译
docker-compose build backend
```

### 前端无法访问后端

**检查网络**:
```bash
# 进入前端容器
docker exec -it corn_frontend sh

# 测试连接
curl http://backend:8000/health
```

**检查 API URL**:
```bash
# 确认环境变量
docker exec corn_frontend env | grep API
```

### 数据库连接失败

**检查数据库状态**:
```bash
docker-compose logs postgres
docker exec corn_postgres pg_isready -U corn_user
```

**重置数据库**:
```bash
docker-compose restart postgres
```

### Python 采集器失败

**检查依赖**:
```bash
docker exec corn_backend pip3 list | grep -E 'requests|beautifulsoup4|lxml'
```

**测试采集器**:
```bash
docker exec corn_backend python3 /app/collectors-python/run_collector.py --collector mock --max-items 5
```

---

## 🛠️ 开发模式

### 本地开发

**后端**:
```bash
cd backend-rust
cargo run
```

**前端**:
```bash
cd frontend
npm install
npm run dev
```

### 热重载

修改代码后：
```bash
# 后端（需要重新构建）
docker-compose build backend
docker-compose up -d backend

# 前端（自动热重载）
# 无需操作，Next.js 会自动重载
```

---

## 📦 生产部署

### 性能优化

1. **使用生产构建**:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

2. **启用 Nginx 反向代理**:
```nginx
upstream backend {
    server localhost:18000;
}

upstream frontend {
    server localhost:3080;
}

server {
    listen 80;
    server_name your-domain.com;
    
    location /api/ {
        proxy_pass http://backend;
    }
    
    location / {
        proxy_pass http://frontend;
    }
}
```

3. **资源限制**:
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 监控和日志

**查看实时日志**:
```bash
docker-compose logs -f --tail=100
```

**导出日志**:
```bash
docker-compose logs > logs/system-$(date +%Y%m%d).log
```

**监控资源使用**:
```bash
docker stats
```

### 备份和恢复

**备份数据库**:
```bash
docker exec corn_postgres pg_dump -U corn_user corn_research > backup-$(date +%Y%m%d).sql
```

**恢复数据库**:
```bash
cat backup.sql | docker exec -i corn_postgres psql -U corn_user -d corn_research
```

**备份 Redis**:
```bash
docker exec corn_redis redis-cli SAVE
docker cp corn_redis:/data/dump.rdb ./backup/
```

---

## 🔐 安全建议

### 生产环境配置

1. **更改默认密码**:
```yaml
POSTGRES_PASSWORD: <strong-password>
REDIS_PASSWORD: <strong-password>
```

2. **使用环境变量文件**:
```bash
# 创建 .env 文件
cp .env.example .env

# 编辑敏感信息
vim .env

# 不要提交 .env 到 Git
echo ".env" >> .gitignore
```

3. **限制网络访问**:
```yaml
services:
  postgres:
    ports:
      - "127.0.0.1:15432:5432"  # 只监听本地
```

4. **启用 SSL/TLS**:
```yaml
services:
  backend:
    environment:
      - RUST_TLS_CERT=/certs/cert.pem
      - RUST_TLS_KEY=/certs/key.pem
```

---

## 📚 维护命令

### 日常维护

```bash
# 查看服务状态
docker-compose ps

# 重启所有服务
docker-compose restart

# 重启单个服务
docker-compose restart backend

# 查看资源使用
docker-compose top

# 清理日志
docker-compose logs --no-log-prefix > /dev/null
```

### 更新系统

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重新构建
docker-compose build

# 3. 重启服务
docker-compose down
docker-compose up -d

# 4. 验证
docker-compose ps
docker-compose logs -f
```

### 清理资源

```bash
# 停止并删除容器
docker-compose down

# 删除所有（包括数据卷）
docker-compose down -v

# 清理悬空镜像
docker image prune -f

# 清理未使用的卷
docker volume prune -f
```

---

## 🆘 获取帮助

### 常用命令

```bash
# 查看完整日志
docker-compose logs

# 进入容器
docker exec -it corn_backend bash

# 检查配置
docker-compose config

# 验证配置文件
docker-compose config --quiet
```

### 诊断信息

收集诊断信息用于报告问题：

```bash
# 系统信息
docker version
docker-compose version

# 服务状态
docker-compose ps -a

# 最近日志
docker-compose logs --tail=100 > diagnostics.log

# 资源使用
docker stats --no-stream >> diagnostics.log
```

---

## 📞 技术支持

- **文档**: 查看项目 README.md
- **Issue**: GitHub Issues
- **日志**: 查看 `docker-compose logs`

---

**最后更新**: 2026-10-21  
**版本**: v2.0.0
