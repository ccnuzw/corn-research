# 🎉 玉米研究系统V2 - 完整启动指南

**日期**: 2026-10-20  
**状态**: ✅ MVP就绪！

---

## 🏗️ 系统架构

```
Next.js前端(:3000) → Rust后端(:8000) → Python采集器 → 数据
```

---

## 🚀 启动步骤

### 1️⃣ 启动Rust后端

```bash
cd /Users/apple/CornV2/backend-rust
cargo run

# 等待看到：
# 🌽 Corn Backend starting on http://127.0.0.1:8000
```

### 2️⃣ 启动Next.js前端（新终端）

```bash
cd /Users/apple/CornV2/frontend
npm install  # 首次需要
npm run dev

# 等待看到：
# ▲ Next.js 14.0.4
# - Local: http://localhost:3000
```

### 3️⃣ 打开浏览器

```
http://localhost:3000
```

---

## 🎯 功能演示

### 查看采集器列表
- 打开浏览器看到2个采集器：博亚和讯、新浪财经

### 启动采集
1. 点击"开始采集"按钮
2. Rust后端调用Python采集器
3. 显示采集结果

### 查看统计
- 总记录数
- 今日新增
- 活跃采集器
- Rust服务状态

---

## 🧪 测试API（可选）

### 终端测试
```bash
# 健康检查
curl http://localhost:8000/health

# 采集器列表
curl http://localhost:8000/api/collectors

# 启动采集
curl -X POST http://localhost:8000/api/collectors/boyar/run

# 系统统计
curl http://localhost:8000/api/data/stats
```

---

## 📊 完整技术栈

| 层次 | 技术 | 端口 |
|------|------|------|
| 前端 | Next.js 14 + TypeScript | 3000 |
| 后端 | Rust (Axum) | 8000 |
| DDD核心 | Rust | - |
| 采集器 | Python | - |
| 数据库 | PostgreSQL | 5432 |

---

## ✅ 已完成功能

- ✅ Rust Web服务（Axum）
- ✅ Python桥接（PyO3）
- ✅ REST API（5个端点）
- ✅ Next.js前端
- ✅ API客户端
- ✅ 采集器集成
- ✅ 实时UI更新

---

## 🎊 成功标志

看到以下界面就成功了：

```
🌽 玉米研究系统 V2
━━━━━━━━━━━━━━━━━━━━━━━━━

📊 统计卡片
┌────────┬────────┬────────┬────────┐
│ 0 记录  │ 0 新增  │ 2 采集器│ ✅ Rust│
└────────┴────────┴────────┴────────┘

📋 采集器列表
🟡 博亚和讯  [开始采集]
🟡 新浪财经  [开始采集]

🚀 快速操作
[最新数据] [数据统计] [Rust服务] [系统设置]
```

---

## 🎯 下一步

1. ✅ **运行系统** - 按上面步骤启动
2. 📝 **测试采集** - 点击"开始采集"按钮
3. 📝 **连接数据库** - PostgreSQL集成
4. 📝 **添加更多功能** - WebSocket、数据可视化

---

**立即开始**: 
```bash
# 终端1
cd backend-rust && cargo run

# 终端2  
cd frontend && npm run dev

# 浏览器
open http://localhost:3000
```

🎉 **恭喜！玉米研究系统V2 MVP完成！** 🎉
