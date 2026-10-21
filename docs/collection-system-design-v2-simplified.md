# 玉米研究系统V2 - 简化版采集管理系统设计

## 📋 设计目标

**核心原则：简单、易用、清晰**

- 不搞复杂概念
- 3个核心对象管理所有采集
- Web UI一目了然
- 自动化处理增量更新和去重

---

## 🎯 三个核心对象

### 1. 数据源 (Source)
- **定义**：采集的目标网站
- **示例**：博亚和讯、新浪财经、DCE期货所
- **作用**：管理网站基本信息和健康状态

### 2. 采集适配器 (Adapter)
- **定义**：一个Python脚本文件
- **示例**：boyar_shandong.py、sina_port.py
- **作用**：实际采集逻辑，可启停、可修改

### 3. 数据主题 (DataTopic)
- **定义**：要采集的指标
- **示例**：山东到车量、北方四港库存、期货价格
- **作用**：查看每种数据来自哪些渠道

---

## 💾 数据库设计

### 核心表结构

```sql
-- 1. 数据源表
CREATE TABLE sources (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    domain VARCHAR(200),
    description TEXT,
    status VARCHAR(20) DEFAULT 'active',  -- active/inactive
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 采集适配器表
CREATE TABLE adapters (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    script_file VARCHAR(200) NOT NULL,     -- Python脚本文件名
    source_id VARCHAR(50) NOT NULL,        -- 关联数据源
    topic_name VARCHAR(100) NOT NULL,      -- 采集的数据主题
    status VARCHAR(20) DEFAULT 'stopped',  -- running/stopped/error
    
    -- 增量更新配置（自动管理）
    last_run_at TIMESTAMP,
    last_cursor VARCHAR(200),              -- 最后采集位置
    
    -- 统计信息
    total_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    last_error TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (source_id) REFERENCES sources(id)
);

-- 3. 采集记录表（简化的RAW+STANDARD合并）
CREATE TABLE collection_records (
    id VARCHAR(50) PRIMARY KEY,
    adapter_id VARCHAR(50) NOT NULL,
    
    -- 业务数据
    business_date DATE NOT NULL,
    value DECIMAL(20, 4),
    unit VARCHAR(20),
    topic_name VARCHAR(100),
    
    -- 溯源信息
    source_url TEXT,
    source_html_path TEXT,                 -- 原始HTML存储路径
    
    -- 质量信息（自动评估）
    quality_grade CHAR(1),                 -- A/B/C/D
    quality_score INTEGER,
    
    -- 时间信息
    collected_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (adapter_id) REFERENCES adapters(id),
    UNIQUE (adapter_id, business_date, topic_name)  -- 防重复
);

-- 4. 采集运行历史表
CREATE TABLE collection_runs (
    id VARCHAR(50) PRIMARY KEY,
    adapter_id VARCHAR(50) NOT NULL,
    
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR(20),                    -- success/failed/running
    
    -- 统计
    new_records INTEGER DEFAULT 0,
    duplicate_records INTEGER DEFAULT 0,
    failed_records INTEGER DEFAULT 0,
    
    -- 游标信息
    start_cursor VARCHAR(200),
    end_cursor VARCHAR(200),
    
    error_message TEXT,
    
    FOREIGN KEY (adapter_id) REFERENCES adapters(id)
);

-- 索引
CREATE INDEX idx_adapters_source ON adapters(source_id);
CREATE INDEX idx_adapters_status ON adapters(status);
CREATE INDEX idx_records_adapter ON collection_records(adapter_id);
CREATE INDEX idx_records_date ON collection_records(business_date DESC);
CREATE INDEX idx_records_topic ON collection_records(topic_name);
CREATE INDEX idx_runs_adapter ON collection_runs(adapter_id);
```

---

## 🔌 API设计

### 数据源管理
```
GET    /api/sources              # 获取所有数据源列表
GET    /api/sources/:id          # 获取数据源详情
POST   /api/sources              # 创建数据源
PUT    /api/sources/:id          # 更新数据源
DELETE /api/sources/:id          # 删除数据源
```

### 采集适配器管理
```
GET    /api/adapters             # 获取所有适配器列表
GET    /api/adapters/:id         # 获取适配器详情
POST   /api/adapters             # 创建适配器
PUT    /api/adapters/:id         # 更新适配器
DELETE /api/adapters/:id         # 删除适配器

POST   /api/adapters/:id/run     # 手动运行采集
POST   /api/adapters/:id/start   # 启动适配器
POST   /api/adapters/:id/stop    # 停止适配器
GET    /api/adapters/:id/runs    # 获取运行历史
GET    /api/adapters/:id/records # 获取采集的数据
```

### 数据主题管理
```
GET    /api/topics               # 获取所有数据主题列表
GET    /api/topics/:name         # 获取主题详情（含所有来源）
GET    /api/topics/:name/records # 获取主题的所有数据
```

### 采集记录查询
```
GET    /api/records              # 查询采集记录
  ?adapter_id=xxx              # 按适配器筛选
  &topic=xxx                   # 按主题筛选
  &start_date=xxx              # 起始日期
  &end_date=xxx                # 结束日期
  &quality=B                   # 按质量等级筛选
```

---

## 🖥️ Web UI设计

### 主界面布局
```
┌─────────────────────────────────────────────┐
│  [侧边栏]     采集管理                      │
│              ━━━━━━━━━━━━━━━━━━━━━━        │
│  Dashboard    [数据源] [适配器] [数据主题]  │
│  采集管理 ●                                 │
│  数据查看                                   │
│  系统设置                                   │
└─────────────────────────────────────────────┘
```

### 页面结构
1. **适配器列表页** - 默认Tab
2. **数据源列表页** - Tab2
3. **数据主题列表页** - Tab3
4. **适配器详情页** - 点击适配器进入
5. **数据查看页** - 点击"查看数据"进入

---

## 🔄 增量更新机制

### 自动化逻辑（用户无感）

```python
def run_adapter(adapter_id):
    """运行采集适配器（自动处理增量）"""
    adapter = get_adapter(adapter_id)
    
    # 1. 自动判断是否首次运行
    is_first_run = (adapter.last_cursor is None)
    
    # 2. 调用Python采集脚本
    if is_first_run:
        results = call_python_script(adapter.script_file, mode='full')
    else:
        results = call_python_script(adapter.script_file, 
                                      mode='incremental',
                                      cursor=adapter.last_cursor)
    
    # 3. 自动去重
    new_records = []
    duplicate_count = 0
    
    for record in results:
        if not exists_in_db(adapter_id, record.business_date):
            new_records.append(record)
        else:
            duplicate_count += 1
    
    # 4. 保存新数据
    save_to_db(new_records)
    
    # 5. 更新游标
    if results:
        adapter.last_cursor = results[-1].cursor
        adapter.last_run_at = now()
        adapter.save()
    
    # 6. 记录本次运行
    save_run_history(adapter_id, {
        'new_records': len(new_records),
        'duplicate_records': duplicate_count,
        'status': 'success'
    })
    
    return {
        'success': True,
        'new_records': len(new_records),
        'duplicates': duplicate_count
    }
```

---

## 📊 质量评估（自动）

```python
def auto_assess_quality(record):
    """自动评估数据质量"""
    score = 0
    
    # 1. 来源可信度 (60分)
    source_scores = {
        'boyahexun.com': 60,
        'sina.com.cn': 55,
        'dce.com.cn': 65
    }
    score += source_scores.get(record.source_domain, 40)
    
    # 2. 数据完整性 (20分)
    if record.value and record.unit and record.business_date:
        score += 20
    
    # 3. 时效性 (20分)
    days_old = (datetime.now() - record.collected_at).days
    if days_old <= 1:
        score += 20
    elif days_old <= 3:
        score += 15
    elif days_old <= 7:
        score += 10
    
    # 评级
    if score >= 85:
        grade = 'B'
    elif score >= 70:
        grade = 'C'
    else:
        grade = 'D'
    
    return grade, score
```

---

## 🚀 实施步骤

### Phase 1: 数据库和后端API (2天)
- [x] 设计数据库表结构
- [ ] 实现SeaORM模型
- [ ] 实现Rust API接口
- [ ] 实现增量更新逻辑

### Phase 2: 前端UI (2天)
- [ ] 实现3个Tab页面
- [ ] 实现适配器列表和详情页
- [ ] 实现数据查看页
- [ ] 集成API调用

### Phase 3: 集成现有采集器 (1天)
- [ ] 迁移博亚和讯采集器
- [ ] 迁移新浪财经采集器
- [ ] 测试增量更新
- [ ] 测试数据溯源

### Phase 4: 测试和优化 (1天)
- [ ] 端到端测试
- [ ] 性能优化
- [ ] Bug修复
- [ ] 文档完善

---

## ✅ 验收标准

1. **功能完整性**
   - ✓ 可以管理数据源、适配器
   - ✓ 可以手动运行采集
   - ✓ 可以查看采集历史
   - ✓ 可以查看采集的数据
   - ✓ 可以追溯数据来源

2. **易用性**
   - ✓ Web UI清晰直观
   - ✓ 操作简单，不超过3次点击
   - ✓ 状态信息一目了然

3. **可靠性**
   - ✓ 增量更新正常工作
   - ✓ 自动去重无误
   - ✓ 质量评估准确
   - ✓ 错误处理完善

---

## 📝 后续优化方向

1. 定时任务调度
2. 实时采集进度展示
3. 采集器健康监控
4. 数据质量报告
5. 批量操作功能

---

**文档版本**: v2.0-simplified  
**创建时间**: 2026-10-21  
**设计者**: 玉米超人  
**批准者**: 刀哥
