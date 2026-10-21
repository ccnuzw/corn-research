# 玉米研究系统V2 - 访问指南

## 🌐 访问地址

### 前端界面
```
http://localhost:3080
```

### 后端API
```
http://localhost:18000/health
http://localhost:18000/api/collectors
```

---

## 🎨 UI特点

### 完全复刻 kiro.rs 设计
- ✅ 5个主题色板可切换
- ✅ 深色/浅色模式
- ✅ 200px侧边导航
- ✅ 统计卡片 + 趋势图表
- ✅ Apple缓动曲线动画
- ✅ 企业级设计标准

### 主要功能
1. **仪表概览** - 系统运行状态
2. **采集器管理** - 数据源监控
3. **数据监控** - 实时数据展示
4. **数据质量** - 质量评分
5. **系统设置** - 配置管理

---

## 🛠️ 开发命令

### Docker方式（推荐）
```bash
cd /Users/apple/CornV2
make up          # 启动所有服务
make logs        # 查看日志
make down        # 停止服务
```

### 容器内开发
```bash
docker-compose exec frontend npm run dev
docker-compose exec backend cargo run
```

---

## 📦 技术栈

- **Next.js 14** - React框架
- **TypeScript** - 类型安全
- **Tailwind CSS** - 原子化CSS
- **Radix UI** - 无障碍组件
- **lucide-react** - 图标库
- **recharts** - 图表库

---

## 🎯 Mock数据

当前使用Mock数据展示，包括：
- 系统统计（总数据量、今日采集等）
- 7天趋势数据
- 4个采集器状态
- 实时成功率

---

**刀哥，访问 http://localhost:3080 查看完整界面！** 🎉🌽
