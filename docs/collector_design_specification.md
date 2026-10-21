# 采集器设计规范

**核心原则**: 一个站点一个专用采集器  
**目标**: 高内聚、低耦合、易维护、易扩展

---

## 一、设计原则

### 1.1 一站一器原则

**✅ 正确做法**:
```
每个数据源站点 = 1个独立采集器类
- 博亚和讯 → BoyarCollector
- 新浪财经 → SinaCollector  
- 大商所 → DCECollector
- 国家统计局 → NBSCollector
- Mysteel → MysteelCollector
```

**❌ 错误做法**:
```
- 一个通用采集器处理多个站点（耦合度高）
- 多个采集器共享解析逻辑（难以维护）
- 站点变化需要修改多个采集器（影响面大）
```

### 1.2 优势

1. **隔离性**: 一个站点变化不影响其他采集器
2. **可测试性**: 每个采集器独立测试
3. **可维护性**: 修改某个站点只需改对应采集器
4. **可扩展性**: 新增站点只需添加新采集器
5. **稳定性**: 一个采集器故障不影响其他
6. **版本控制**: 每个采集器独立版本号

---

## 二、采集器目录结构

```
infrastructure/collectors/
├── base/
│   ├── __init__.py
│   └── base_collector.py              # 抽象基类
│
├── official/                          # 官方数据源
│   ├── __init__.py
│   ├── dce_collector.py              # 大商所
│   ├── cbot_collector.py             # CBOT
│   ├── nbs_collector.py              # 国家统计局
│   └── moa_collector.py              # 农业农村部
│
├── commercial/                        # 商业数据源
│   ├── __init__.py
│   ├── mysteel_collector.py          # Mysteel钢联
│   ├── wind_collector.py             # Wind万得
│   ├── zhuochuang_collector.py       # 卓创资讯
│   └── huiyi_collector.py            # 汇易网
│
├── public_media/                      # 公开媒体
│   ├── __init__.py
│   ├── boyar_collector.py            # 博亚和讯
│   ├── sina_collector.py             # 新浪财经
│   ├── netease_collector.py          # 网易订阅
│   ├── qq_collector.py               # 腾讯新闻
│   ├── eastmoney_collector.py        # 东方财富
│   └── hexun_collector.py            # 和讯财经
│
├── industry/                          # 行业网站
│   ├── __init__.py
│   ├── hubei_grain_collector.py      # 湖北粮网
│   ├── china_grain_collector.py      # 中华粮网
│   └── enongzi_collector.py          # 农资与市场
│
└── registry.py                        # 采集器注册表
```

---

## 三、采集器标准模板

### 3.1 基类定义

```python
# infrastructure/collectors/base/base_collector.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class CollectorStatus(Enum):
    """采集器状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class BaseCollector(ABC):
    """
    采集器抽象基类
    
    每个站点必须实现一个独立的采集器类
    """
    
    # ==================== 必须实现的属性 ====================
    
    @property
    @abstractmethod
    def collector_id(self) -> str:
        """
        采集器唯一标识
        格式: {source_type}_{site_name}
        例如: public_media_boyar
        """
        pass
    
    @property
    @abstractmethod
    def site_name(self) -> str:
        """站点名称，例如: 博亚和讯"""
        pass
    
    @property
    @abstractmethod
    def site_url(self) -> str:
        """站点首页URL"""
        pass
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """
        来源类型
        - official_government: 政府官方
        - official_exchange: 交易所官方
        - commercial_primary: 一手商业数据
        - public_media: 公开媒体
        - industry_portal: 行业门户
        """
        pass
    
    @property
    @abstractmethod
    def supported_data_types(self) -> List[str]:
        """
        支持的数据类型
        例如: ['price', 'inventory', 'arrivals']
        """
        pass
    
    @property
    @abstractmethod
    def collection_frequency(self) -> str:
        """
        采集频率
        - realtime: 实时
        - hourly: 每小时
        - daily: 每日
        - weekly: 每周
        """
        pass
    
    @property
    def version(self) -> str:
        """采集器版本"""
        return "1.0.0"
    
    # ==================== 必须实现的方法 ====================
    
    @abstractmethod
    async def collect(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        执行采集
        
        Returns:
            List[Dict]: 原始采集记录列表
        
        Raises:
            CollectionError: 采集失败
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        验证配置
        
        Returns:
            bool: 配置是否有效
        """
        pass
    
    # ==================== 可选覆盖的方法 ====================
    
    async def pre_collect(self) -> None:
        """采集前钩子（可选实现）"""
        pass
    
    async def post_collect(self, records: List[Dict[str, Any]]) -> None:
        """采集后钩子（可选实现）"""
        pass
    
    def calculate_reliability_score(
        self,
        data_completeness: float,
        timeliness_hours: int
    ) -> float:
        """
        计算可靠度分数（可覆盖）
        
        默认实现基于来源类型、完整性和时效性
        """
        # 来源基础分
        tier_scores = {
            'official_government': 1.0,
            'official_exchange': 1.0,
            'commercial_primary': 0.9,
            'public_media': 0.7,
            'industry_portal': 0.7
        }
        base_score = tier_scores.get(self.source_type, 0.5)
        
        # 时效性调整
        if timeliness_hours < 24:
            timeliness_factor = 1.0
        elif timeliness_hours < 72:
            timeliness_factor = 0.9
        elif timeliness_hours < 168:
            timeliness_factor = 0.8
        else:
            timeliness_factor = 0.6
        
        return round(
            base_score * data_completeness * timeliness_factor,
            2
        )
```

### 3.2 具体实现示例：博亚和讯

```python
# infrastructure/collectors/public_media/boyar_collector.py
import re
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..base.base_collector import BaseCollector


class BoyarCollector(BaseCollector):
    """
    博亚和讯采集器
    
    站点: https://m.boyar.cn
    数据: 山东到车、价格、开机率
    频率: 每30分钟
    版本: 2.0.0
    """
    
    # ==================== 属性实现 ====================
    
    @property
    def collector_id(self) -> str:
        return "public_media_boyar"
    
    @property
    def site_name(self) -> str:
        return "博亚和讯"
    
    @property
    def site_url(self) -> str:
        return "https://m.boyar.cn"
    
    @property
    def source_type(self) -> str:
        return "public_media"
    
    @property
    def supported_data_types(self) -> List[str]:
        return ["arrivals", "spot_price", "processing_rate"]
    
    @property
    def collection_frequency(self) -> str:
        return "30min"
    
    @property
    def version(self) -> str:
        return "2.0.0"
    
    # ==================== 配置 ====================
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.base_url = "https://m.boyar.cn"
        self.timeout = self.config.get('timeout', 10)
        self.max_retries = self.config.get('max_retries', 3)
    
    def validate_config(self) -> bool:
        """验证配置"""
        return True  # 博亚和讯无需特殊配置
    
    # ==================== 核心采集逻辑 ====================
    
    async def collect(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        执行采集
        
        策略: 按文章ID范围扫描
        """
        # 确定ID范围
        start_id = kwargs.get('start_id') or self._estimate_article_id(start_date)
        end_id = kwargs.get('end_id') or self._estimate_article_id(end_date)
        
        # 并发采集
        records = []
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._fetch_article(session, article_id)
                for article_id in range(start_id, end_id + 1)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    records.extend(result)
        
        return records
    
    async def _fetch_article(
        self,
        session: aiohttp.ClientSession,
        article_id: int
    ) -> List[Dict[str, Any]]:
        """
        获取单篇文章
        
        这是博亚和讯特有的逻辑
        """
        url = f"{self.base_url}/article/{article_id}.html"
        
        try:
            async with session.get(url, timeout=self.timeout) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 提取元数据
                title = self._extract_title(soup)
                published_at = self._extract_publish_time(soup)
                content = self._extract_content(soup)
                
                # 应用提取规则
                records = []
                records.extend(
                    self._extract_arrivals(content, published_at, url, title)
                )
                records.extend(
                    self._extract_prices(content, published_at, url, title)
                )
                
                return records
                
        except Exception as e:
            # 记录错误但不中断
            return []
    
    def _extract_arrivals(
        self,
        content: str,
        published_at: datetime,
        url: str,
        title: str
    ) -> List[Dict[str, Any]]:
        """
        提取到车量
        
        规则:
        1. "X月X日.*山东.*到车.*数字"
        2. "山东深加工.*到车.*数字"
        """
        records = []
        
        # 规则1
        pattern = r'(\d{1,2})月(\d{1,2})日.*?山东.*?到车.*?(\d+)'
        for match in re.finditer(pattern, content):
            month = int(match.group(1))
            day = int(match.group(2))
            value = float(match.group(3))
            
            # 推断年份
            year = published_at.year
            if month > published_at.month:
                year -= 1
            
            business_date = datetime(year, month, day)
            
            records.append({
                'business_date': business_date,
                'published_at': published_at,
                'data_type': 'arrivals',
                'indicator': '山东深加工到车量',
                'value': value,
                'unit': '台',
                'region': '山东',
                'source_url': url,
                'original_text': match.group(0),
                'metadata': {
                    'title': title,
                    'article_id': url.split('/')[-1].replace('.html', ''),
                    'extraction_rule': 'pattern1'
                }
            })
        
        return records
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """提取标题（博亚和讯特定）"""
        title_elem = soup.select_one('h1.title')
        return title_elem.text.strip() if title_elem else ''
    
    def _extract_publish_time(self, soup: BeautifulSoup) -> datetime:
        """提取发布时间（博亚和讯特定）"""
        time_elem = soup.select_one('.publish-time')
        if time_elem:
            time_str = time_elem.text.strip()
            # 解析时间字符串
            return self._parse_time(time_str)
        return datetime.now()
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """提取正文（博亚和讯特定）"""
        content_elem = soup.select_one('.article-body')
        return content_elem.text if content_elem else ''
    
    # ==================== 辅助方法 ====================
    
    def _estimate_article_id(self, date: Optional[datetime]) -> int:
        """
        根据日期估算文章ID
        
        博亚和讯特有：文章ID与日期有大致对应关系
        """
        if not date:
            return 1267500  # 默认起始ID
        
        # 简化估算逻辑
        days_since_base = (date - datetime(2026, 9, 1)).days
        return 1265000 + days_since_base * 20
    
    def _parse_time(self, time_str: str) -> datetime:
        """解析时间字符串"""
        # 实现具体解析逻辑
        pass
```

### 3.3 新浪财经采集器

```python
# infrastructure/collectors/public_media/sina_collector.py
class SinaCollector(BaseCollector):
    """
    新浪财经采集器
    
    站点: https://finance.sina.com.cn
    数据: 北港库存、下海量、价格
    频率: 每日
    版本: 2.0.0
    """
    
    @property
    def collector_id(self) -> str:
        return "public_media_sina"
    
    @property
    def site_name(self) -> str:
        return "新浪财经"
    
    # ... 其他属性
    
    async def collect(self, **kwargs) -> List[Dict[str, Any]]:
        """
        新浪财经的采集逻辑
        
        与博亚和讯完全不同的实现
        """
        # 新浪特有的采集逻辑
        pass
```

---

## 四、采集器注册表

```python
# infrastructure/collectors/registry.py
from typing import Dict, Type
from .base.base_collector import BaseCollector

class CollectorRegistry:
    """采集器注册表"""
    
    _collectors: Dict[str, Type[BaseCollector]] = {}
    
    @classmethod
    def register(cls, collector_class: Type[BaseCollector]) -> None:
        """
        注册采集器
        
        使用装饰器自动注册:
        @CollectorRegistry.register
        class BoyarCollector(BaseCollector):
            pass
        """
        instance = collector_class()
        cls._collectors[instance.collector_id] = collector_class
    
    @classmethod
    def get(cls, collector_id: str) -> Type[BaseCollector]:
        """获取采集器类"""
        return cls._collectors.get(collector_id)
    
    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        """列出所有采集器"""
        return [
            {
                'collector_id': cid,
                'site_name': cls().site_name,
                'source_type': cls().source_type,
                'version': cls().version
            }
            for cid, cls in cls._collectors.items()
        ]


# 使用装饰器注册
@CollectorRegistry.register
class BoyarCollector(BaseCollector):
    pass

@CollectorRegistry.register
class SinaCollector(BaseCollector):
    pass
```

---

## 五、采集器开发清单

### P0优先级（当前）
- [ ] BoyarCollector - 博亚和讯
- [ ] SinaCollector - 新浪财经
- [ ] DCECollector - 大商所
- [ ] NeteaseCollector - 网易订阅

### P1优先级（近期）
- [ ] NBSCollector - 国家统计局
- [ ] MysteelCollector - Mysteel（需授权）
- [ ] HubeiGrainCollector - 湖北粮网
- [ ] QQCollector - 腾讯新闻

### P2优先级（后期）
- [ ] ZhuochuangCollector - 卓创资讯
- [ ] CBOTCollector - CBOT
- [ ] WindCollector - Wind万得

---

## 六、优势总结

### ✅ 一站一器的好处

1. **隔离性强**
   - 博亚和讯改版 → 只需修改BoyarCollector
   - 不影响SinaCollector、DCECollector等

2. **测试独立**
   ```python
   # 只测试博亚和讯
   pytest tests/collectors/test_boyar_collector.py
   ```

3. **版本清晰**
   ```
   BoyarCollector v2.0.0 → v2.1.0
   SinaCollector v1.5.0 不变
   ```

4. **故障隔离**
   - 博亚和讯挂了 → 其他采集器正常工作
   - 不会级联故障

5. **并行开发**
   - 开发者A: BoyarCollector
   - 开发者B: SinaCollector
   - 无冲突

---

**这才是真正的企业级设计**！准备好按这个规范实施了吗？
