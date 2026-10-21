# 🎯 Docker快速启动指南

## 🚀 一键启动（3步）

### 1. 构建镜像
```bash
cd /Users/apple/CornV2
make docker-build
```
⏱️ **预计时间**: 5-10分钟（Rust编译较慢，首次）

### 2. 启动服务
```bash
make up
```
⏱️ **预计时间**: 30秒

### 3. 访问
- **前端**: http://localhost:3000
- **后端**: http://localhost:8000/health

---

## 📊 当前状态

### ✅ 已完成
- ✅ Dockerfile（Rust后端 + PyO3）
- ✅ docker-compose.yml（4服务编排）
- ✅ Makefile（快捷命令）
- ✅ 完整文档

### ⚠️ 待修复
- ⚠️ 前端构建问题（已简化为dev模式）
- ⚠️ Rust后端需要验证编译

### 🎯 下一步
测试Docker构建：
```bash
make docker-build
```

---

## 🐛 问题排查

### 前端构建失败
**已修复**: 改用开发模式，无需构建

### Rust编译慢
**正常**: 首次5-10分钟，之后有缓存1-2分钟

### 端口冲突
```bash
# 修改 docker-compose.yml
ports:
  - "3001:3000"
```

---

## 💡 临时方案

如果Docker构建遇到问题，可以先用：

### CLI方式（立即可用）
```bash
make dev-cli
```

### 本地启动基础设施
```bash
make infra-up        # 只启动数据库+Redis
make dev-cli         # 启动CLI
```

---

**刀哥，现在测试`make docker-build`，看Rust能否成功编译！** 🚀
