# Docker健康检查修复说明

## 问题描述
Docker Compose中的后端服务健康检查显示 `unhealthy` 状态。

## 根本原因
`docker-compose.yml` 中的健康检查命令使用了：
```yaml
test: ["CMD", "corn-backend", "--version"]
```

由于 `corn-backend` 二进制程序没有实现命令行参数解析（如 `--version`），当健康检查执行该命令时：
1. 程序忽略 `--version` 参数
2. 尝试启动完整的Web服务器
3. 尝试绑定 8000 端口
4. **与主容器进程发生端口冲突**
5. 健康检查失败，返回 `unhealthy`

## 解决方案
将健康检查改为使用 HTTP 请求检测 `/health` 端点：

**修改前：**
```yaml
healthcheck:
  test: ["CMD", "corn-backend", "--version"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s
```

**修改后：**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s
```

## 优势
✅ 真正检测服务是否在运行（HTTP响应）  
✅ 不会引起端口冲突  
✅ 检测速度快（3-5秒内响应）  
✅ 与 Dockerfile 中的健康检查方式保持一致  

## 验证方法
重新启动服务并检查健康状态：

```bash
# 重建并启动服务
docker-compose up -d --build backend

# 检查健康状态
docker-compose ps

# 查看详细健康检查日志
docker inspect corn_backend | grep -A 10 Health

# 手动测试健康检查命令
docker exec corn_backend curl -f http://localhost:8000/health
```

预期输出：
```json
{
  "success": true,
  "data": "Corn Backend V2 is running",
  "message": null
}
```

## 相关文件
- `docker-compose.yml` (第 67-72 行) - 已修复
- `Dockerfile` (第 72-73 行) - 已使用正确的 curl 方式
- `backend-rust/src/main.rs` (第 163-169 行) - `/health` 端点实现

---
修复日期: 2025-01-XX
