# 玉米研究系统V2 - 基于CARF超级框架的采集系统终极设计

**设计时间**: 2026-10-20 21:30
**基于**: CARF超级框架 (玉米研究智能体超级框架.html)

---

## 1. 核心理解：采集在CARF中的位置

### 1.1 CARF五层能力栈
```
┌─────────────────────────────────────┐
│ ROLE AGENTS (责任与草稿)            │  AG-FACT负责事实核验
├─────────────────────────────────────┤
│ THREE-LAYER SKILLS (方法与反证)     │  领域Skill定义采集规则
├─────────────────────────────────────┤
│ ENGINES → TOOLS (确定性计算)        │  验证、去重、质量分级
├─────────────────────────────────────┤
│ DATA CONNECTORS (来源与权限) ←───── │  **采集器在这一层**
├─────────────────────────────────────┤
│ CARF HARNESS (运行治理)             │  冻结、强制、记录、降级
└─────────────────────────────────────┘
```

**关键认知**：
- 采集器是**DATA CONNECTORS**层的实现
- 输出直接进入**市场总账(ART-MKT-*)**
- 必须服从**CARF HARNESS**的治理约束

### 1.2 研究经营闭环中的采集
```
事实与证据 → 因果与状态 → 情景与价格 → 敞口与策略 → 执行与复盘
    ↑                                                     ↓
    └──────────── 反馈：归因、校准、新版本 ──────────────┘
```

**采集职责**：
- 为"事实与证据"提供**原始输入**
- 附带**来源、时间、口径**三要素
- 区分**可核验事实 vs 观点推断**

---

## 2. 采集什么？（完整覆盖15个领域维度）

### 2.1 市场总账 ART-MKT-001：市场事实快照

#### 定量事实（必采）

| 领域 | 对象 | 数据源 | 频率 | 口径 |
|------|------|--------|------|------|
| **农业生产** | 面积、天气、单产、生育期 | 农业部、气象局、USDA | 周/月 | 播种/收获/年度产量 |
| **国内供给** | 产量、农户余粮、政策粮 | CASDE、统计局、粮食局 | 月度 | 年度/季度/月度平衡 |
| **进口替代** | 进口玉米、小麦、高粱、DDGS | 海关、港口、CFT | 周/月 | 到港/配额/成本 |
| **饲料养殖** | 存栏、补栏、利润、采购 | Mysteel、饲料协会 | 周/月 | 能繁母猪/生猪/蛋禽 |
| **深加工** | 开机率、产品价格、利润 | CFT、企业报价 | 周更 | 淀粉/酒精/糖浆 |
| **库存结构** | 位置、所有权、可动性 | 港口、企业、贸易商 | 周更 | 北港/销区/深加工 |
| **区域流通** | 到车、发运、运费、基差 | 博亚、湖北粮网、物流商 | 日/周 | 山东到车/集港/下海 |
| **区域现货** | 报价、成交、贸易流 | CFT、100ppi、产业链 | 日更 | 东北/华北/华南 |
| **期现基差** | 期现差、跨期、仓单 | DCE、期货公司 | 交易日 | 主力/近月/远月 |
| **资金信用** | 融资、账期、保证金 | 银行、企业授权 | 周/月 | 贸易融资/信用额度 |

#### 定价与情绪（重要）
| 对象 | 数据源 | 频率 | 说明 |
|------|--------|------|------|
| 预期与叙事 | 期货公司、社交媒体 | 日/周 | 共识、拥挤、计价程度 |
| 持仓结构 | DCE、期权持仓 | 交易日 | 大户、基金、套保 |
| 价格异常 | 自动监控 | 实时 | 触发反向研究任务 |

### 2.2 市场总账 ART-MKT-006：证据、事件与政策账本

#### 政策类（A级证据）
| 对象 | 数据源 | 频率 | 必采字段 |
|------|--------|------|----------|
| 国储拍卖 | 粮食交易中心 | 事件 | 时间、数量、底价、成交率 |
| 进口政策 | 海关、商务部 | 事件 | 配额、关税、检疫、生效日期 |
| 监管政策 | 发改委、粮食局 | 事件 | 政策内容、执行范围、影响区域 |
| 补贴政策 | 农业部、财政部 | 事件 | 补贴标准、范围、发放时间 |

#### 研报与观点（C级，需交叉验证）
| 对象 | 数据源 | 频率 | 类型 |
|------|--------|------|------|
| 期货公司日报 | 各期货公司官网 | 日更 | **完整HTML** + 观点摘要 |
| 期货公司周报 | 各期货公司官网 | 周更 | **完整PDF** + 逻辑链提取 |
| USDA报告 | USDA官网 | 月度 | **完整报告** + 数据表 |
| 产业调研 | Mysteel、企业 | 不定期 | 一手调研、访谈、现场 |
| CFT快讯 | CFT、粮油信息网 | 日更 | 产业新闻、市场动态 |

#### 天气与物流（事件类）
| 对象 | 数据源 | 频率 | 说明 |
|------|--------|------|------|
| 天气预报 | 气象局、天气网 | 日更 | 关键生育期、灾害预警 |
| 物流异常 | 交通部、贸易商 | 事件 | 运输受阻、港口拥堵 |
| 疫情封控 | 卫健委、地方政府 | 事件 | 影响流通的管控措施 |

---

## 3. 数据采集架构（五段血缘）

### 3.1 完整血缘链
```
RAW (原始事实)
    ↓ 供应商、报告、现场、行情、业务填报
STANDARD (标准事实)
    ↓ 业务时间、披露时间、口径、质量、修订
DERIVED (派生指标)
    ↓ 平衡表、到货、基差、替代成本、状态分数
RUN (场景运行)
    ↓ 基准、参数、模型、智能体、异常、中间结果
DECISION (执行与归因)
    ↓ 建议、审批、动作、费用、风险变化、复盘
```

**关键约束**：
- ✅ **禁止用后续修订数据覆盖历史认知快照**
- ✅ 每段必须保留：as-of时间、版本、来源、质量
- ✅ 修订必须归因：为什么改、改了什么、谁改的

### 3.2 数据库表结构（三层+血缘）

#### RAW层：raw_collection_records
```sql
CREATE TABLE raw_collection_records (
    id UUID PRIMARY KEY,
    source_id VARCHAR NOT NULL,
    collected_at TIMESTAMP NOT NULL,
    published_at TIMESTAMP,
    disclosure_time TIMESTAMP, -- 披露时间（CARF要求）
    source_url TEXT NOT NULL,
    raw_html TEXT,
    raw_text TEXT,
    raw_pdf_path TEXT,
    content_type VARCHAR, -- 'price', 'report', 'policy', 'news'
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_raw_source_time ON raw_collection_records(source_id, collected_at);
```

#### STANDARD层：market_facts_standard
```sql
CREATE TABLE market_facts_standard (
    id UUID PRIMARY KEY,
    raw_record_id UUID REFERENCES raw_collection_records(id),
    artifact_type VARCHAR NOT NULL, -- 'ART-MKT-001', 'ART-MKT-006' etc
    domain VARCHAR NOT NULL, -- '农业生产', '区域流通' etc
    indicator_name VARCHAR NOT NULL,
    business_date DATE NOT NULL,
    disclosure_time TIMESTAMP NOT NULL,
    value NUMERIC,
    unit VARCHAR,
    region VARCHAR,
    quality_grade CHAR(1), -- A/B/C/D (CARF质量分级)
    caliber TEXT, -- 口径说明（CARF核心要求）
    revision_risk VARCHAR, -- 修订风险（高/中/低）
    coverage TEXT, -- 覆盖范围说明
    freshness_hours INT,
    dedup_key VARCHAR UNIQUE,
    version INT DEFAULT 1,
    is_revision BOOLEAN DEFAULT FALSE,
    revision_reason TEXT,
    validated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_standard_artifact ON market_facts_standard(artifact_type, business_date);
CREATE INDEX idx_standard_indicator ON market_facts_standard(indicator_name, business_date);
```

#### DERIVED层：market_artifacts
```sql
CREATE TABLE market_artifacts (
    id UUID PRIMARY KEY,
    artifact_id VARCHAR NOT NULL, -- 'ART-MKT-001-20261020-001'
    artifact_type VARCHAR NOT NULL,
    snapshot_time TIMESTAMP NOT NULL,
    data_as_of_date DATE NOT NULL, -- CARF: 数据截至时点
    content JSONB NOT NULL,
    source_facts JSONB, -- 引用的standard层记录IDs
    derivation_method TEXT,
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(artifact_id, version)
);
```

---

## 4. 采集器设计（基于CARF DATA CONNECTORS）

### 4.1 采集器分类

#### Class A：定量事实采集器（高频）
```python
class QuantitativeFactCollector(BaseCollector):
    """定量事实采集器基类"""
    artifact_type = "ART-MKT-001"
    quality_grade = QualityGrade.B
    
    def extract_caliber(self, raw: RawRecord) -> str:
        """提取口径说明（CARF核心要求）"""
        raise NotImplementedError
        
    def extract_revision_risk(self, raw: RawRecord) -> str:
        """判断修订风险"""
        # 农业部产量：高修订风险
        # 港口库存：低修订风险
        return "medium"
```

**具体实现**：
- DCE期货采集器（A级）
- 博亚山东到车采集器（B级）
- 新浪北港周报采集器（B级）
- CFT现货报价采集器（B级）

#### Class B：政策与事件采集器（事件触发）
```python
class PolicyEventCollector(BaseCollector):
    """政策与事件采集器"""
    artifact_type = "ART-MKT-006"
    quality_grade = QualityGrade.A  # 官方政策A级
    
    def extract_event_structure(self, raw: RawRecord) -> dict:
        """结构化事件（CARF要求）"""
        return {
            "event_type": "policy",  # policy/weather/logistics
            "impact_domains": ["进口与替代", "国内供给"],
            "effective_date": "2026-10-20",
            "impact_regions": ["全国"],
            "verification_conditions": ["配额实际执行量"]
        }
```

**具体实现**：
- 粮食交易中心拍卖采集器（A级）
- 海关政策采集器（A级）
- 气象灾害采集器（B级）

#### Class C：研报与观点采集器（定性证据）
```python
class ResearchReportCollector(BaseCollector):
    """研报采集器 - 保留完整原文"""
    artifact_type = "ART-MKT-006"
    quality_grade = QualityGrade.C  # 需交叉验证
    
    def collect(self) -> List[RawRecord]:
        """采集完整PDF/HTML，不只是摘要"""
        # 1. 下载完整PDF
        # 2. 保存HTML快照
        # 3. 提取观点和逻辑链
        pass
        
    def extract_logic_chain(self, raw: RawRecord) -> dict:
        """提取逻辑链（CARF要求）"""
        return {
            "conclusion": "看涨Q4价格",
            "logic_chain": [
                "产量下调 → 库存收紧",
                "需求改善 → 补库预期",
                "运费上涨 → 流通受阻"
            ],
            "key_assumptions": ["天气无重大变化", "进口配额不变"],
            "invalidation_conditions": ["库存超预期累积"]
        }
```

**具体实现**：
- 期货公司日报采集器（完整HTML+观点）
- 期货公司周报采集器（完整PDF+逻辑链）
- USDA报告采集器（完整报告+数据表）
- CFT快讯采集器（产业新闻）

---

## 5. 质量分级与验证（CARF标准）

### 5.1 CARF四级质量体系

| 等级 | 定义 | 示例 | 操作 |
|------|------|------|------|
| **A** | 权威原始来源 | DCE官网、USDA、海关 | 直接进入STANDARD层 |
| **B** | 可靠业务来源/多源验证 | 博亚、CFT、期货公司 | 经验证后进入STANDARD |
| **C** | 单一调研/二手来源 | 期货公司观点、贸易商消息 | 交叉验证后可升B |
| **D** | 未验证线索 | 社交媒体传闻 | 阻塞，必须人工核查 |

### 5.2 口径验证引擎
```python
class CaliberValidator:
    """口径验证器（CARF核心要求）"""
    
    def validate_caliber(self, fact: StandardFact) -> ValidationResult:
        """验证口径一致性"""
        conflicts = []
        
        # 1. 检查单位一致性
        if fact.indicator_name == "山东深加工到车量":
            if fact.unit != "台":
                conflicts.append("单位冲突：应为'台'")
        
        # 2. 检查统计口径
        if "日度" in fact.caliber and "周度" in fact.caliber:
            conflicts.append("周期口径冲突")
        
        # 3. 检查区域口径
        if "山东" in fact.region and "全国" in fact.caliber:
            conflicts.append("区域口径冲突")
        
        if conflicts:
            return ValidationResult(
                valid=False,
                conflicts=conflicts,
                action="BLOCK"  # 阻塞，不进入STANDARD层
            )
        
        return ValidationResult(valid=True)
```

---

## 6. Web UI功能（对标CARF PlanGraph）

### 6.1 采集器管理页面
```
┌─────────────────────────────────────────────┐
│ 采集器管理 / DATA CONNECTORS                 │
├─────────────────────────────────────────────┤
│ 过滤: [领域▼] [质量等级▼] [状态▼] [搜索...]  │
├─────────────────────────────────────────────┤
│ ✓ DCE期货采集器      │ A级 │ 运行中 │ 2分钟前 │
│   博亚到车采集器      │ B级 │ 空闲   │ 1小时前 │
│   新浪北港周报采集器  │ B级 │ 空闲   │ 3小时前 │
│   国储拍卖采集器      │ A级 │ 空闲   │ 1天前   │
│   期货公司日报采集器  │ C级 │ 运行中 │ 5分钟前 │
└─────────────────────────────────────────────┘
```

### 6.2 数据血缘浏览
```
┌─────────────────────────────────────────────┐
│ 数据血缘 / DATA LINEAGE                      │
├─────────────────────────────────────────────┤
│ ART-MKT-001-20261020-山东到车-B001           │
├─────────────────────────────────────────────┤
│ RAW → 博亚和讯HTML (2026-10-20 08:30)        │
│   ↓                                          │
│ STANDARD → 山东到车550台 (B级, 日度晨间口径) │
│   ↓                                          │
│ DERIVED → 市场事实快照 (ART-MKT-001)        │
│   ↓                                          │
│ RUN → 场景推演 (区域流通状态判断)           │
│   ↓                                          │
│ DECISION → 暂不行动 (供应充裕，持有压力)    │
└─────────────────────────────────────────────┘
```

### 6.3 质量监控看板
```
┌─────────────────────────────────────────────┐
│ 质量监控 / QUALITY DASHBOARD                 │
├─────────────────────────────────────────────┤
│ 质量分布:  A级: 12%  B级: 65%  C级: 20%  D级: 3% │
├─────────────────────────────────────────────┤
│ ⚠ 口径冲突: 3条 (需人工复核)                 │
│ ⚠ 修订风险: 北港库存修订-15% (已标记)         │
│ ✓ 新鲜度: P0指标全部 < 72h                   │
│ ✓ 交叉验证: 山东到车3源一致                   │
└─────────────────────────────────────────────┘
```

---

## 7. 实施计划（4周 → 8周MVP）

### Week 1-2: 核心定量采集器
- [ ] DCE期货采集器（A级）
- [ ] 博亚山东到车采集器（B级）
- [ ] 新浪北港周报采集器（B级）
- [ ] RAW + STANDARD表 + 血缘链
- [ ] Web UI：采集器列表 + 启停

### Week 3-4: 政策与事件采集
- [ ] 粮食交易中心拍卖采集器（A级）
- [ ] 海关政策采集器（A级）
- [ ] 事件结构化引擎
- [ ] ART-MKT-006表
- [ ] Web UI：事件浏览

### Week 5-6: 研报与观点采集
- [ ] 期货公司日报采集器（完整HTML）
- [ ] 期货公司周报采集器（完整PDF）
- [ ] 逻辑链提取引擎
- [ ] 观点交叉验证引擎
- [ ] Web UI：研报库 + 观点对比

### Week 7-8: 质量与血缘
- [ ] 口径验证引擎
- [ ] 修订风险标记
- [ ] 完整血缘追溯
- [ ] DERIVED层自动生成
- [ ] Web UI：质量看板 + 血缘图

---

## 8. 关键差异总结（vs 之前设计）

| 维度 | 之前设计 | CARF设计 |
|------|----------|----------|
| 采集范围 | 主要价格数据 | **价格+研报+政策+观点** |
| 数据层次 | 原始→候选→主链 | **RAW→STANDARD→DERIVED→RUN→DECISION（五段血缘）** |
| 质量分级 | A/B/C | **A/B/C/D + 口径验证 + 修订风险** |
| 溯源要求 | 基本溯源 | **禁止覆盖历史快照 + 版本血缘** |
| 研报处理 | 未覆盖 | **完整HTML/PDF + 逻辑链提取** |
| 政策事件 | 未覆盖 | **事件结构化 + 影响路径** |
| 产物归属 | 自定义表 | **四本总账（ART-MKT-*）** |

---

**刀哥，这个基于CARF超级框架的设计，关键是：**

1. **不只采价格**：研报、政策、观点、逻辑链都要采
2. **五段血缘**：RAW→STANDARD→DERIVED→RUN→DECISION
3. **禁止覆盖**：历史快照永不修改，修订必须归因
4. **口径验证**：单位、周期、区域口径必须一致
5. **质量分级**：A/B/C/D + 交叉验证升级机制

**这才是CARF要求的完整采集系统！准备开始实施了吗？** 🌽✨
