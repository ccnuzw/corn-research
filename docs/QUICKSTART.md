# 🚀 玉米研究系统V2 - 启动指南

**架构**: Next.js → Rust(Axum) → Python采集器

---

## 📦 安装依赖

### 1. Rust后端
```bash
cd /Users/apple/CornV2/backend-rust
cargo build --release
```

### 2. Next.js前端
```bash
cd /Users/apple/CornV2/frontend
npm install
```

### 3. Python采集器
```bash
cd /Users/apple/CornV2
source .venv/bin/activate
pip install requests beautifulsoup4 lxml
```

---

## 🎯 启动系统

### 步骤1: 启动Rust后端
```bash
cd /Users/apple/CornV2/backend-rust
cargo run

# 输出：
# 🌽 Corn Backend starting on http://127.0.0.1:8000
```

### 步骤2: 启动Next.js前端
```bash
cd /Users/apple/CornV2/frontend
npm run dev

# 输出：
# ▲ Next.js 14.0.4
# - Local: http://localhost:3000
```

### 步骤3: 访问管理界面
```
打开浏览器: http://localhost:3000
```

---

## 🧪 测试API

### 测试后端健康检查
```bash
curl http://localhost:8000/health
# {"success":true,"data":"Corn Backend is running","message":null}
```

### 测试采集器列表
```bash
curl http://localhost:8000/api/collectors
```

### 测试启动采集
```bash
curl -X POST http://localhost:8000/api/collectors/boyar/run
```

---

## 🏗️ 完整架构

```
用户浏览器
    ↓
http://localhost:3000 (Next.js前端)
    ↓ HTTP API
http://localhost:8000 (Rust后端 Axum)
    ↓ PyO3
Python采集器 (BoyarCollector)
    ↓
PostgreSQL (数据存储)
```

---

## 📊 API端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/collectors` | 获取采集器列表 |
| POST | `/api/collectors/{id}/run` | 启动采集 |
| GET | `/api/data/latest` | 最新数据 |
| GET | `/api/data/stats` | 系统统计 |

---

## 🎊 当前状态

✅ Rust后端框架完成  
✅ Python桥接实现  
✅ Next.js前端框架完成  
📝 API集成待完成  
📝 数据库连接待完成  

---

**下一步**: 编译Rust后端并测试！

```bash
cd /Users/apple/CornV2/backend-rust
cargo build
cargo run
```
