# 玉米研究系统V2 - 基于CARF框架的采集系统完整设计

**设计时间**: 2026-10-20 21:15
**基于**: CARF研究框架 + 四本总账体系

---

## 1. 为什么要采集？（基于CARF的定位）

### 核心目标
采集是**市场总账（ART-MKT-*）**的数据输入层，为整个研究体系提供**可信事实**基础。

### 采集在研究闭环中的位置
```
数据采集 → 质量与口径判断 → 市场总账 → 因果分析 → 状态识别 
→ 情景更新 → 价格映射 → 经营影响 → 条件化建议
```

**关键认知**：
- ✅ 采集不是目的，是**可信事实的唯一入口**
- ✅ 每条数据必须支持**追溯、证伪和版本管理**
- ✅ 事实、推断、预测、建议**必须分层**

---

## 2. 采集什么？（基于CARF研究对象）

### 2.1 市场事实快照 (ART-MKT-001)

#### A. 价格类数据
| 对象 | 数据源 | 频率 | 字段 |
|------|--------|------|------|
| DCE期货 | 大商所官网 | 交易日 | 合约、收盘价、结算价、成交量、持仓量 |
| CBOT期货 | CME官网 | 交易日 | 合约、价格、成交量、外盘联动 |
| 现货报价 | CFT、100ppi、Mysteel | 日更 | 区域、品种、报价、成交、升贴水 |
| 基差 | 期货公司 | 日更 | 区域、基差、历史分位 |

#### B. 供需平衡表数据 (ART-MKT-002)
| 对象 | 数据源 | 频率 | 字段 |
|------|--------|------|------|
| 产量预测 | USDA、农业部、私人机构 | 月度 | 面积、单产、产量、修订 |
| 库存数据 | CASDE、海关、企业 | 周度/月度 | 地点、类型、数量、可流通 |
| 消费数据 | 饲料协会、深加工协会 | 月度 | 饲料、深加工、种用、出口 |
| 进口数据 | 海关 | 月度 | 数量、来源国、到港、配额 |

#### C. 区域流通数据 (ART-MKT-003)
| 对象 | 数据源 | 频率 | 字段 |
|------|--------|------|------|
| 山东深加工到车量 | 博亚、湖北粮网、腾讯新闻 | 日更 | 日期、台数、区域 |
| 北港库存+下海量 | 新浪周报、期货公司 | 周更 | 库存、下海量、港口明细 |
| 集港发运量 | CFT、贸易商 | 周更 | 发运量、路线、运费 |
| 销区到货 | 各地粮网 | 日/周更 | 地点、到货量、采购价 |

#### D. 替代品数据
| 对象 | 数据源 | 频率 | 说明 |
|------|--------|------|------|
| 小麦价格 | CFT、郑商所 | 日更 | 价格、替代比例 |
| 高粱/大麦 | 海关、港口 | 周更 | 进口、到港、价格 |
| DDGS | 企业报价 | 周更 | 价格、供应、配方比 |

#### E. 养殖与加工数据
| 对象 | 数据源 | 频率 | 字段 |
|------|--------|------|------|
| 生猪存栏 | 农业部、Mysteel | 月度 | 能繁母猪、生猪存栏 |
| 饲料产量 | 饲料协会 | 月度 | 产量、配方、原料消耗 |
| 深加工开机率 | CFT、企业 | 周更 | 开机率、产品价格、利润 |

### 2.2 证据、事件与政策账本 (ART-MKT-006)

#### A. 政策文件
| 对象 | 数据源 | 频率 | 字段 |
|------|--------|------|------|
| 国储拍卖 | 粮食交易中心 | 事件 | 时间、数量、底价、成交率 |
| 进口政策 | 海关、商务部 | 事件 | 配额、关税、检疫 |
| 监管政策 | 发改委、粮食局 | 事件 | 政策内容、执行范围 |

#### B. 行业报告与研报
| 对象 | 数据源 | 频率 | 类型 |
|------|--------|------|------|
| 期货公司日报 | 各期货公司官网 | 日更 | 观点、数据、逻辑链 |
| 期货公司周报 | 各期货公司官网 | 周更 | 深度分析、情景推演 |
| 产业调研 | Mysteel、产业链 | 不定期 | 一手调研、访谈 |
| USDA报告 | USDA | 月度 | 全球供需、库存预测 |

#### C. 新闻与点评
| 对象 | 数据源 | 频率 | 类型 |
|------|--------|------|------|
| 产业新闻 | CFT、粮油信息网 | 日更 | 事件、影响 |
| 天气新闻 | 气象局、天气网 | 日更 | 天气、灾害、影响区域 |
| 市场传闻 | 微信群、贸易商 | 实时 | 传闻、验证、确认 |

---

## 3. 采集架构（三层+四本总账）

### 3.1 采集三层架构

```
┌─────────────────────────────────────────────────┐
│  原始采集层 (Raw Collection Layer)                │
│  - Python采集器                                   │
│  - 完整原文、URL、时间戳                           │
│  - append-only，永不修改                          │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│  验证与结构化层 (Validation & Structuring)         │
│  - 字段提取与规范化                                │
│  - 质量分级（A/B/C/D）                            │
│  - 去重检查                                       │
│  - 口径对齐                                       │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│  市场总账层 (Market Ledger)                       │
│  - ART-MKT-001: 市场事实快照                      │
│  - ART-MKT-002: 供需平衡表                        │
│  - ART-MKT-003: 区域流通                          │
│  - ART-MKT-004: 库存结构                          │
│  - ART-MKT-005: 期现定价                          │
│  - ART-MKT-006: 证据事件                          │
└─────────────────────────────────────────────────┘
```

### 3.2 数据库表结构

#### raw_records（原始层）
```sql
CREATE TABLE raw_records (
    id UUID PRIMARY KEY,
    source_id VARCHAR NOT NULL,
    collected_at TIMESTAMP NOT NULL,
    published_at TIMESTAMP,
    source_url TEXT,
    raw_html TEXT,
    raw_text TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### structured_facts（验证层）
```sql
CREATE TABLE structured_facts (
    id UUID PRIMARY KEY,
    raw_record_id UUID REFERENCES raw_records(id),
    source_id VARCHAR NOT NULL,
    indicator_name VARCHAR NOT NULL,
    business_date DATE NOT NULL,
    value NUMERIC,
    unit VARCHAR,
    region VARCHAR,
    quality_grade CHAR(1), -- A/B/C/D
    reliability VARCHAR,
    caliber VARCHAR,
    revision_risk VARCHAR,
    coverage VARCHAR,
    freshness_hours INT,
    dedup_key VARCHAR UNIQUE,
    validated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### market_facts_snapshot（市场总账 ART-MKT-001）
```sql
CREATE TABLE market_facts_snapshot (
    id UUID PRIMARY KEY,
    fact_type VARCHAR NOT NULL,
    market VARCHAR,
    region VARCHAR,
    object VARCHAR,
    indicator VARCHAR NOT NULL,
    value NUMERIC NOT NULL,
    unit VARCHAR NOT NULL,
    business_date DATE NOT NULL,
    snapshot_time TIMESTAMP NOT NULL,
    vs_previous NUMERIC,
    vs_year_ago NUMERIC,
    historical_percentile NUMERIC,
    caliber VARCHAR,
    source_refs JSONB,
    quality_grade CHAR(1),
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 4. 采集器设计（基于CARF证据质量）

### 4.1 采集器基类
```python
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

class QualityGrade(Enum):
    A = "A"  # 权威原始来源
    B = "B"  # 可靠业务来源或多源交叉验证
    C = "C"  # 单一现场/调研或可信二手来源
    D = "D"  # 未验证线索

@dataclass
class RawRecord:
    """原始采集记录"""
    source_id: str
    collected_at: datetime
    published_at: Optional[datetime]
    source_url: str
    raw_html: str
    raw_text: str
    metadata: dict

@dataclass
class StructuredFact:
    """结构化事实"""
    raw_record_id: str
    source_id: str
    indicator_name: str
    business_date: datetime
    value: float
    unit: str
    region: str
    quality_grade: QualityGrade
    reliability: str
    caliber: str
    coverage: str
    freshness_hours: int

class BaseCollector:
    """采集器基类"""
    
    def __init__(self, source_id: str, quality_grade: QualityGrade):
        self.source_id = source_id
        self.quality_grade = quality_grade
        
    def collect(self) -> List[RawRecord]:
        """采集原始数据"""
        raise NotImplementedError
        
    def extract(self, raw: RawRecord) -> List[StructuredFact]:
        """提取结构化事实"""
        raise NotImplementedError
        
    def validate(self, fact: StructuredFact) -> bool:
        """验证事实"""
        # 必填字段
        if not all([fact.business_date, fact.value, fact.unit]):
            return False
        # 新鲜度检查
        if fact.freshness_hours > self.get_freshness_threshold():
            return False
        return True
        
    def get_freshness_threshold(self) -> int:
        """获取新鲜度阈值（小时）"""
        # 根据指标类型设置不同阈值
        return 72  # 默认3天
```

### 4.2 具体采集器示例

#### 山东深加工到车量（B级）
```python
class BoyarShandongArrivalsCollector(BaseCollector):
    """博亚和讯 - 山东深加工到车量"""
    
    def __init__(self):
        super().__init__(
            source_id="corn_boyar_shandong_arrivals",
            quality_grade=QualityGrade.B
        )
        
    def collect(self) -> List[RawRecord]:
        url = "https://www.boyar.cn/shandong/arrivals"
        html = requests.get(url).text
        
        return [RawRecord(
            source_id=self.source_id,
            collected_at=datetime.now(),
            published_at=self.extract_publish_time(html),
            source_url=url,
            raw_html=html,
            raw_text=BeautifulSoup(html, 'lxml').get_text(),
            metadata={"collector_version": "1.0"}
        )]
        
    def extract(self, raw: RawRecord) -> List[StructuredFact]:
        soup = BeautifulSoup(raw.raw_html, 'lxml')
        facts = []
        
        for row in soup.select('.data-table tr'):
            date_str = row.select_one('.date').text.strip()
            value_str = row.select_one('.value').text.strip()
            
            facts.append(StructuredFact(
                raw_record_id=raw.id,
                source_id=self.source_id,
                indicator_name="山东深加工到车量",
                business_date=parse_date(date_str),
                value=parse_number(value_str),
                unit="台",
                region="山东",
                quality_grade=QualityGrade.B,
                reliability="high",
                caliber="日度晨间到车",
                coverage="山东主要深加工企业",
                freshness_hours=calculate_hours(date_str)
            ))
        
        return facts
```

#### DCE期货（A级）
```python
class DCEFuturesCollector(BaseCollector):
    """大商所期货数据 - A级权威来源"""
    
    def __init__(self):
        super().__init__(
            source_id="dce_corn_futures",
            quality_grade=QualityGrade.A
        )
```

#### 期货公司日报（C级→结构化后可升B）
```python
class FuturesCompanyDailyCollector(BaseCollector):
    """期货公司日报 - 需要交叉验证"""
    
    def __init__(self, company: str):
        super().__init__(
            source_id=f"futures_daily_{company}",
            quality_grade=QualityGrade.C  # 默认C级
        )
        
    # 交叉验证后可升级为B
    def cross_validate(self, facts: List[StructuredFact]) -> List[StructuredFact]:
        """多源交叉验证后升级质量"""
        # 检查是否有独立来源验证
        # 如果验证通过，升级为B级
        pass
```

---

## 5. 采集内容分类（对标CARF）

### 5.1 按产物类型分类

| 产物类型 | 采集内容 | 频率 | 质量要求 |
|----------|----------|------|----------|
| ART-MKT-001 市场事实 | 价格、成交、库存、产量 | 日/周/月 | A/B级 |
| ART-MKT-002 供需平衡 | 产量、消费、进口、库存 | 月度 | A/B级 |
| ART-MKT-003 区域流通 | 到车、发运、运费、基差 | 日/周 | B级 |
| ART-MKT-006 证据事件 | 政策、新闻、研报、调研 | 事件/日 | B/C级 |

### 5.2 按证据类型分类

#### 定量事实（必须采集）
- ✅ 价格（期货、现货、基差）
- ✅ 数量（库存、产量、消费、进口）
- ✅ 流通（到车、发运、集港）
- ✅ 质量（水分、容重、等级）

#### 定性信息（重要补充）
- ✅ 政策文件（收储、拍卖、进口）
- ✅ 行业报告（日报、周报、月报）
- ✅ 市场观点（看涨/看跌、逻辑链）
- ✅ 调研信息（现场、访谈、传闻）

#### 原文与上下文（完整溯源）
- ✅ HTML原文
- ✅ 发布时间
- ✅ 来源URL
- ✅ 口径说明
- ✅ 修订历史

---

## 6. 采集管理（Web UI功能）

### 6.1 采集器管理页面
- ✅ 采集器列表（名称、状态、质量等级、最后运行）
- ✅ 启动/停止/手动触发
- ✅ 调度配置（cron表达式）
- ✅ 运行日志查看
- ✅ 统计数据（成功/失败/去重）

### 6.2 数据浏览页面
- ✅ 原始记录浏览（按来源、时间）
- ✅ 结构化事实浏览（按指标、区域）
- ✅ 市场总账浏览（ART-MKT-001等）
- ✅ 完整溯源链（原始→结构化→总账）

### 6.3 质量监控页面
- ✅ 质量等级统计（A/B/C/D分布）
- ✅ 新鲜度告警（过期数据）
- ✅ 冲突数据列表（多源不一致）
- ✅ 待验证队列（C/D级数据）

---

## 7. 下一步实施（4周计划）

### Week 1: 核心采集器
- [ ] DCE期货采集器（A级）
- [ ] 博亚山东到车采集器（B级）
- [ ] 新浪北港周报采集器（B级）
- [ ] 原始记录表+结构化表

### Week 2: 验证与总账
- [ ] 质量分级引擎
- [ ] 去重引擎
- [ ] 市场事实快照表（ART-MKT-001）
- [ ] Web UI：采集器管理

### Week 3: 研报与政策
- [ ] 期货公司日报采集器（C级）
- [ ] 政策文件采集器（A级）
- [ ] 证据事件账本（ART-MKT-006）
- [ ] Web UI：数据浏览

### Week 4: 监控与优化
- [ ] 新鲜度监控
- [ ] 质量告警
- [ ] 交叉验证引擎
- [ ] Web UI：质量监控

---

**刀哥，这个基于CARF的完整设计清楚了吗？关键是：**
1. 采集→验证→总账 三层分离
2. 完整溯源（原文+URL+时间+质量）
3. 不只是价格，还有政策、研报、调研
4. 质量分级（A/B/C/D）并支持交叉验证升级

**接下来从哪里开始实施？** 🌽
