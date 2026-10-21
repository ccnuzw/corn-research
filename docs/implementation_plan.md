# 玉米研究系统V2 实施计划

**启动日期**: 2026-10-20  
**预计完成**: 2026-12-15（8周）  
**状态**: ✅ Week 0 已完成

---

## ✅ Week 0: 项目初始化（已完成）

### 完成清单
- [x] Git仓库初始化
- [x] 项目目录结构
- [x] 主题系统设计（6套主题）
- [x] Docker Compose配置
- [x] 数据库Schema（TimescaleDB）
- [x] Python依赖清单
- [x] Next.js项目配置
- [x] README和文档

### 已创建文件
```
/Users/apple/CornV2/
├── README.md
├── docker-compose.yml
├── docs/
│   └── themes.md
├── backend/
│   ├── requirements.txt
│   └── db/migrations/001_initial_schema.sql
└── frontend/
    └── package.json
```

---

## 📋 Week 1: 后端基础设施（本周）

### Day 1-2: FastAPI核心
- [ ] FastAPI应用结构
  - [ ] `app/main.py` - 应用入口
  - [ ] `app/core/config.py` - 配置管理
  - [ ] `app/core/database.py` - 数据库连接
  - [ ] `app/core/redis.py` - Redis连接
  - [ ] `app/core/logging.py` - 日志系统

- [ ] API路由框架
  - [ ] `app/api/routes/` - 路由目录
  - [ ] 健康检查端点 `/health`
  - [ ] 版本信息端点 `/version`

### Day 3-4: 数据模型
- [ ] Pydantic模型
  - [ ] `app/models/price.py` - 价格模型
  - [ ] `app/models/fundamental.py` - 基本面模型
  - [ ] `app/models/source.py` - 数据源模型
  - [ ] `app/models/collector.py` - 采集器模型

- [ ] SQLAlchemy ORM
  - [ ] `app/db/models.py` - ORM模型
  - [ ] `app/db/crud.py` - CRUD操作

### Day 5-7: 采集器基类
- [ ] `app/collectors/base.py` - 采集器基类
  - [ ] `BaseCollector`抽象类
  - [ ] `collect()`抽象方法
  - [ ] `validate_before_save()`验证方法
  - [ ] `calculate_reliability_score()`评分方法

- [ ] 采集器注册表
  - [ ] `app/collectors/registry.py`
  - [ ] 自动发现机制
  - [ ] 采集器元数据

**本周交付物**:
- ✅ FastAPI应用可启动
- ✅ 数据库连接正常
- ✅ 基础API端点工作
- ✅ 采集器基类可用

---

## 📋 Week 2: 前端基础设施

### Day 1-2: Next.js基础
- [ ] Next.js应用结构
  - [ ] `src/app/layout.tsx` - 根布局
  - [ ] `src/app/page.tsx` - 首页
  - [ ] `src/lib/utils.ts` - 工具函数
  - [ ] `src/lib/api.ts` - API客户端

- [ ] Shadcn/ui集成
  - [ ] Tailwind配置
  - [ ] 基础组件安装
  - [ ] 主题系统实现

### Day 3-4: 布局组件
- [ ] `src/components/layout/` - 布局组件
  - [ ] `Header.tsx` - 顶部栏
  - [ ] `Sidebar.tsx` - 侧边栏
  - [ ] `Footer.tsx` - 底部栏

- [ ] 主题切换器
  - [ ] `src/components/theme-switcher.tsx`
  - [ ] `src/hooks/use-theme.ts`
  - [ ] 6套主题CSS实现

### Day 5-7: 基础页面
- [ ] 页面路由
  - [ ] `/` - 首页
  - [ ] `/monitor` - 监控中心
  - [ ] `/collectors` - 采集器管理
  - [ ] `/data` - 数据浏览
  - [ ] `/settings` - 设置

- [ ] 基础组件
  - [ ] `KPICard` - KPI卡片
  - [ ] `StatusBadge` - 状态徽章
  - [ ] `LoadingSpinner` - 加载动画

**本周交付物**:
- ✅ Next.js应用可访问
- ✅ 主题切换功能正常
- ✅ 布局完整可用
- ✅ 页面路由工作

---

## 📋 Week 3: 核心采集器（博亚+新浪）

### Day 1-3: 博亚和讯V2
- [ ] `app/collectors/boyar.py`
  - [ ] 文章列表采集
  - [ ] 文章内容解析
  - [ ] 数据提取规则
    - [ ] 山东到车量
    - [ ] 山东现货价格
    - [ ] 开机率
  - [ ] 质量评分逻辑
  - [ ] 单元测试

### Day 4-5: 新浪财经V2
- [ ] `app/collectors/sina.py`
  - [ ] 北港周报采集
  - [ ] 日度价格采集
  - [ ] 数据提取规则
    - [ ] 北方四港库存
    - [ ] 北方四港下海量
    - [ ] 各地价格
  - [ ] 质量评分逻辑
  - [ ] 单元测试

### Day 6-7: 采集任务调度
- [ ] `app/scheduler/`
  - [ ] 采集任务定义
  - [ ] Cron调度器
  - [ ] 并发控制
  - [ ] 重试机制
  - [ ] 日志记录

**本周交付物**:
- ✅ 博亚和讯自动采集
- ✅ 新浪财经自动采集
- ✅ 数据写入数据库
- ✅ 采集日志可查

---

## 📋 Week 4: 核心采集器（DCE+网易）

### Day 1-3: DCE期货数据
- [ ] `app/collectors/dce.py`
  - [ ] DCE API对接
  - [ ] 实时行情采集
  - [ ] 日结算数据
  - [ ] 历史数据回填
  - [ ] 基差计算
  - [ ] 单元测试

### Day 4-5: 网易订阅自动化
- [ ] `app/collectors/netease.py`
  - [ ] RSS/Atom订阅
  - [ ] 文章自动发现
  - [ ] 内容解析
  - [ ] 数据提取
  - [ ] 单元测试

### Day 6-7: 数据API开发
- [ ] API端点
  - [ ] `GET /api/prices` - 价格查询
  - [ ] `GET /api/fundamentals` - 基本面查询
  - [ ] `GET /api/futures` - 期货查询
  - [ ] `GET /api/sources` - 数据源状态
  - [ ] WebSocket `/ws/realtime` - 实时推送

**本周交付物**:
- ✅ DCE期货实时采集
- ✅ 网易订阅自动化
- ✅ 数据API可用
- ✅ WebSocket实时推送

---

## 📋 Week 5: 质量保障系统

### Day 1-2: 多源交叉验证
- [ ] `app/services/validation.py`
  - [ ] `CrossSourceValidator`类
  - [ ] 同指标多源对比
  - [ ] 离群值检测
  - [ ] 加权平均计算
  - [ ] 置信度评估

### Day 3-4: 时序异常检测
- [ ] `app/services/anomaly.py`
  - [ ] `TimeSeriesAnomalyDetector`类
  - [ ] 移动平均计算
  - [ ] Z-score异常检测
  - [ ] 自动告警触发

### Day 5-7: 人工审核界面
- [ ] 前端页面 `/data/review`
  - [ ] 待审核数据列表
  - [ ] 溯源信息展示
  - [ ] 快速审核操作
  - [ ] 批量处理
  - [ ] 审核历史记录

**本周交付物**:
- ✅ 多源验证工作
- ✅ 异常检测生效
- ✅ 审核界面可用
- ✅ 数据质量提升

---

## 📋 Week 6: 可视化监控

### Day 1-3: 采集监控中心
- [ ] 页面 `/monitor`
  - [ ] 实时KPI统计
  - [ ] 采集器进度条
  - [ ] 实时日志流
  - [ ] 性能图表
  - [ ] 健康状态面板

### Day 4-5: 数据溯源界面
- [ ] 组件 `SourceTraceModal`
  - [ ] 时间线展示
  - [ ] 原文链接
  - [ ] 提取详情
  - [ ] 质量评分可视化
  - [ ] 操作按钮

### Day 6-7: 图表组件
- [ ] ECharts集成
  - [ ] 价格走势图
  - [ ] 库存变化图
  - [ ] 基差分析图
  - [ ] 热力图
  - [ ] K线图

**本周交付物**:
- ✅ 监控中心完整
- ✅ 溯源功能可用
- ✅ 图表美观专业
- ✅ 实时更新流畅

---

## 📋 Week 7: 扩展数据源

### Day 1-2: 国家统计局
- [ ] `app/collectors/nbs.py`
  - [ ] API对接
  - [ ] 产量数据
  - [ ] 库存数据
  - [ ] 历史数据

### Day 3-4: Mysteel（如有授权）
- [ ] `app/collectors/mysteel.py`
  - [ ] API认证
  - [ ] 价格数据
  - [ ] 库存数据
  - [ ] 开机率数据

### Day 5-7: 数据导出功能
- [ ] 导出API
  - [ ] CSV导出
  - [ ] Excel导出
  - [ ] PDF报告
  - [ ] 定制报告模板

**本周交付物**:
- ✅ 官方数据源接入
- ✅ 商业源接入（可选）
- ✅ 数据导出功能
- ✅ 报告生成功能

---

## 📋 Week 8: 优化与部署

### Day 1-2: 性能优化
- [ ] 后端优化
  - [ ] 数据库查询优化
  - [ ] 索引优化
  - [ ] 缓存策略
  - [ ] 异步优化

- [ ] 前端优化
  - [ ] 代码分割
  - [ ] 懒加载
  - [ ] 图片优化
  - [ ] 首屏优化

### Day 3-4: 部署准备
- [ ] Docker镜像优化
- [ ] 生产环境配置
- [ ] Nginx配置
- [ ] SSL证书
- [ ] 备份策略

### Day 5-7: 测试与文档
- [ ] 端到端测试
- [ ] 性能测试
- [ ] 用户文档
- [ ] API文档
- [ ] 运维手册

**本周交付物**:
- ✅ 系统性能优秀
- ✅ 生产环境就绪
- ✅ 文档完整
- ✅ V2正式发布

---

## 🎯 里程碑检查点

### Milestone 1: 基础设施就绪（Week 2结束）
- [ ] 前后端可独立运行
- [ ] 数据库正常工作
- [ ] 基础API可用
- [ ] UI布局完整

### Milestone 2: 核心采集上线（Week 4结束）
- [ ] 4个核心采集器运行
- [ ] 数据持续写入
- [ ] 监控面板可视化
- [ ] 实时推送正常

### Milestone 3: 质量保障完成（Week 6结束）
- [ ] 多源验证生效
- [ ] 异常检测工作
- [ ] 审核流程顺畅
- [ ] 数据溯源完整

### Milestone 4: 生产就绪（Week 8结束）
- [ ] 系统稳定运行
- [ ] 性能达标
- [ ] 文档齐全
- [ ] 可对外演示

---

## 📊 成功指标

### 数据指标
- 采集成功率 > 95%
- 数据延迟 < 1小时
- 质量评分 > 0.8
- 覆盖率 > 90%

### 性能指标
- API响应时间 < 500ms
- 页面加载时间 < 2s
- 实时推送延迟 < 1s
- 并发支持 > 100用户

### 质量指标
- 多源一致性 > 95%
- 异常检测准确率 > 90%
- 零数据丢失
- 完整溯源链

---

## 🚀 下一步行动

**立即开始Week 1 Day 1**:
1. 创建FastAPI应用结构
2. 实现配置管理
3. 连接数据库
4. 启动开发服务器

**命令**:
```bash
cd /Users/apple/CornV2/backend
mkdir -p app/{api,core,models,db,collectors,services,scheduler}
touch app/__init__.py app/main.py app/core/__init__.py
```

准备好了吗？开工！🎉
