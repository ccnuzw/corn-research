# 玉米研究系统V2 - 采集功能完整设计方案

**设计时间**: 2026-10-20 21:00
**基于**: 旧Corn项目经验 + 企业级DDD架构

---

## 1. 采集功能是什么？

### 核心目标
从多个公开/商业数据源自动抓取玉米市场基本面数据，经过验证、清洗、去重、质量分级后，进入候选层或主链，为市场分析提供可靠数据基础。

### 关键价值
- ✅ **自动化**: 替代人工每日复制粘贴
- ✅ **溯源性**: 每条数据保留完整来源链路
- ✅ **质量保证**: 多层验证，分级管理
- ✅ **实时性**: P0指标滞后≤3天

---

## 2. 采集什么内容？

### 2.1 P0核心指标（4个）
基于旧项目的P0 SLO要求：

#### A. 山东深加工到车量
- **数据源**: 博亚和讯、湖北粮网、腾讯新闻、农资与市场、期货公司周报
- **字段**: 日期、到车量（台）、区域、来源
- **频率**: 日更
- **当前状态**: 最新至2026-10-19，仍缺6天

#### B. 北方四港库存 + 下海量
- **数据源**: 新浪财经周报、期货公司周报、中国饲料工业信息网
- **字段**: 周度、库存（万吨）、下海量（万吨）、港口明细
- **频率**: 周更
- **当前状态**: 已达标（2026-10-07）

#### C. DCE玉米期货
- **数据源**: 大连商品交易所官网
- **字段**: 合约、收盘价、结算价、成交量、持仓量
- **频率**: 交易日更新
- **当前状态**: 已达标

#### D. CBOT玉米期货
- **数据源**: CME官网
- **字段**: 合约、价格、成交量、外盘联动
- **频率**: 交易日更新
- **当前状态**: 待实现

### 2.2 候选补充指标
- 饲料厂采购价
- 售粮进度
- 深加工开机率
- 替代品价格（小麦、高粱、大麦、DDGS）

---

## 3. 采集架构设计

### 3.1 技术栈
```
Next.js前端 (React)
    ↓ REST API
Rust Axum后端 (Web服务)
    ↓ PyO3 FFI
Python采集器 (requests + BeautifulSoup4 + lxml)
    ↓ 写入
PostgreSQL数据库 (三层表结构)
```

### 3.2 三层数据治理

#### 原始层 (raw_records)
- **不可修改**: append-only
- **完整溯源**: 业务时间、采集时间、发布时间、来源URL、原文
- **字段**: 
  ```sql
  id, source_id, indicator_name, value, unit, region, 
  business_date, collected_at, published_at, 
  source_url, raw_text, quality, reliability
  ```

#### 候选层 (candidate)
- **准入验证**: 必须通过准入规则
- **去重**: hash(source_id + business_date + indicator + value)
- **质量分级**: B/C/Unknown
- **可晋升**: 仅B级可晋升主链

#### 主链 (master)
- **权威数据**: 供分析使用
- **完整溯源**: 保留从原始→候选→主链的完整血统
- **SLO保证**: P0指标滞后≤3天

### 3.3 质量分级标准

| 等级 | 标准 | 行动 |
|------|------|------|
| B (可靠) | 官方源/商业一手源，字段完整，可验证 | 允许晋升主链 |
| C (存疑) | 转载链/部分字段缺失/口径不明 | 仅候选层，不晋升 |
| Unknown | 质量未评估 | 阻塞，必须人工评级 |

---

## 4. 采集器如何工作？

### 4.1 采集器基类设计 (Python)
```python
class BaseCollector:
    """所有采集器的基类"""
    
    def __init__(self, source_id: str):
        self.source_id = source_id
        
    def collect(self) -> List[RawRecord]:
        """执行采集，返回原始记录列表"""
        # 1. 发起HTTP请求
        # 2. 解析HTML/JSON
        # 3. 提取字段
        # 4. 构造RawRecord对象
        # 5. 返回列表
        pass
        
    def validate(self, record: RawRecord) -> bool:
        """验证单条记录"""
        # 必填字段检查
        # 数据类型检查
        # 范围合理性检查
        pass
```

### 4.2 具体采集器示例
```python
class BoyarCollector(BaseCollector):
    """博亚和讯 - 山东深加工到车量"""
    
    def __init__(self):
        super().__init__("corn_boyar_shandong_arrivals")
        self.url = "https://www.boyar.cn/news/corn"
        
    def collect(self) -> List[RawRecord]:
        # 访问页面
        html = requests.get(self.url).text
        soup = BeautifulSoup(html, 'lxml')
        
        # 提取数据
        records = []
        for row in soup.select('.data-table tr'):
            date = row.select_one('.date').text
            value = row.select_one('.value').text
            
            records.append(RawRecord(
                source_id=self.source_id,
                indicator_name="山东深加工到车量",
                value=parse_int(value),
                unit="台",
                business_date=parse_date(date),
                collected_at=datetime.now(),
                source_url=self.url,
                raw_text=row.text,
                quality="B",
                reliability="high"
            ))
        
        return records
```

### 4.3 Rust桥接层 (PyO3)
```rust
#[pyfunction]
fn run_collector(collector_name: &str) -> PyResult<Vec<PyRawRecord>> {
    // 调用Python采集器
    Python::with_gil(|py| {
        let collector = py.import("collectors")?
            .getattr(collector_name)?
            .call0()?;
            
        let records = collector.call_method0("collect")?;
        records.extract()
    })
}
```

---

## 5. 采集器管理

### 5.1 采集器元数据
```sql
CREATE TABLE collectors (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    source_id VARCHAR NOT NULL,
    status VARCHAR, -- 'active', 'idle', 'error', 'disabled'
    schedule VARCHAR, -- cron表达式
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    success_count INT,
    error_count INT,
    config JSONB
);
```

### 5.2 管理功能
- ✅ 启动/停止采集器
- ✅ 手动触发单次运行
- ✅ 查看运行日志
- ✅ 配置调度计划
- ✅ 查看统计数据

---

## 6. 数据验证流程

### 6.1 验证层级
```
原始记录
    ↓ 字段完整性验证
候选记录
    ↓ 去重验证
    ↓ 质量分级验证
    ↓ 业务规则验证
主链记录
```

### 6.2 验证规则示例
```rust
impl ValidationService {
    fn validate_record(&self, record: &RawRecord) -> Result<ValidationResult> {
        // 1. 必填字段
        if record.business_date.is_none() {
            return Err(ValidationError::MissingDate);
        }
        
        // 2. 数值范围
        if record.value < 0.0 || record.value > 10000.0 {
            return Err(ValidationError::OutOfRange);
        }
        
        // 3. 来源白名单
        if !self.allowed_sources.contains(&record.source_id) {
            return Err(ValidationError::UnknownSource);
        }
        
        Ok(ValidationResult::Valid)
    }
}
```

---

## 7. 数据保存流程

### 7.1 保存策略
```
1. 原始记录 → raw_records表 (append-only)
2. 通过验证 → candidate表
3. 去重检查 → 如果重复则跳过
4. 质量B级 → 允许晋升master表
5. 更新统计 → 更新采集器成功计数
```

### 7.2 去重策略
```rust
fn generate_dedup_key(record: &Record) -> String {
    format!(
        "{}:{}:{}:{}",
        record.source_id,
        record.business_date,
        record.indicator_name,
        record.value
    )
}
```

---

## 8. Web UI功能清单

### 8.1 采集器管理页
- [x] 采集器列表（表格）
- [ ] 启动/停止按钮
- [ ] 手动触发运行
- [ ] 查看详情
- [ ] 配置编辑
- [ ] 删除采集器
- [ ] 新建采集器

### 8.2 数据监控页
- [ ] 实时采集状态
- [ ] 数据新鲜度监控
- [ ] P0指标SLO看板
- [ ] 异常告警列表

### 8.3 数据质量页
- [ ] 质量评分统计
- [ ] 问题记录列表
- [ ] 待人工审核队列
- [ ] 质量趋势图

### 8.4 数据浏览页
- [ ] 候选数据列表
- [ ] 主链数据列表
- [ ] 数据详情（完整溯源）
- [ ] 手动晋升/降级

---

## 9. API设计

### 9.1 采集器管理API
```
GET    /api/collectors          # 列表
POST   /api/collectors          # 创建
GET    /api/collectors/:id      # 详情
PUT    /api/collectors/:id      # 更新
DELETE /api/collectors/:id      # 删除
POST   /api/collectors/:id/run  # 手动运行
POST   /api/collectors/:id/stop # 停止
```

### 9.2 数据查询API
```
GET /api/records/raw        # 原始记录
GET /api/records/candidate  # 候选记录
GET /api/records/master     # 主链记录
GET /api/indicators/:name   # 按指标查询
```

---

## 10. 关键问题解答

### Q1: 如何保证数据不重复？
**A**: 三重保护
1. 候选层去重（hash key）
2. 主链晋升前去重
3. 数据库unique约束

### Q2: 如何验证数据质量？
**A**: 四层验证
1. 字段完整性（Rust ValidationService）
2. 数值范围合理性
3. 来源可靠性分级（B/C）
4. 人工审核队列（C级数据）

### Q3: 采集失败怎么办？
**A**: 容错机制
1. 记录错误日志
2. 更新采集器error_count
3. 状态标记为'error'
4. Web UI显示告警
5. 下次调度时自动重试

### Q4: 如何管理多个采集器？
**A**: 中心化管理
1. collectors表存储元数据
2. Rust Axum提供统一API
3. Next.js前端提供可视化管理
4. 支持批量启停、调度配置

### Q5: 历史数据如何补齐？
**A**: 手动补齐+自动填充
1. 创建临时采集器
2. 指定日期范围
3. 批量抓取历史数据
4. 进入候选层走正常晋升流程

---

## 11. 下一步实施计划

### Phase 1: 核心采集器（1周）
- [ ] BoyarCollector（山东到车）
- [ ] SinaCollector（北港周报）
- [ ] DCECollector（期货）

### Phase 2: 管理界面（1周）
- [ ] 采集器列表+启停
- [ ] 运行日志查看
- [ ] 数据浏览

### Phase 3: 验证+晋升（1周）
- [ ] 去重服务
- [ ] 质量分级
- [ ] 候选→主链晋升

### Phase 4: 监控+告警（1周）
- [ ] SLO监控
- [ ] 异常告警
- [ ] 数据质量看板

---

**刀哥，这个设计方案清楚了吗？需要我深入展开哪部分？** 🌽
