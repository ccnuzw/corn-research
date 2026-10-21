# 玉米研究系统V2 - DDD架构设计

**架构模式**: 领域驱动设计（Domain-Driven Design）  
**分层**: 清晰的职责分离 + 依赖倒置  
**目标**: 企业级标准 + 易于维护和扩展

---

## 一、DDD分层架构

```
┌─────────────────────────────────────────┐
│       Presentation Layer（表现层）        │
│  - REST API (FastAPI)                  │
│  - WebSocket                           │
│  - GraphQL (可选)                      │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│      Application Layer（应用层）         │
│  - Use Cases / Application Services    │
│  - DTOs                                │
│  - Command/Query Handlers              │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│        Domain Layer（领域层）            │
│  - Entities（实体）                     │
│  - Value Objects（值对象）              │
│  - Aggregates（聚合根）                 │
│  - Domain Services（领域服务）          │
│  - Domain Events（领域事件）            │
│  - Repository Interfaces（仓储接口）    │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│    Infrastructure Layer（基础设施层）     │
│  - Repository Implementations          │
│  - ORM (SQLAlchemy)                    │
│  - External Services                   │
│  - Collectors                          │
│  - Cache (Redis)                       │
│  - Message Queue                       │
└─────────────────────────────────────────┘
```

---

## 二、项目目录结构（DDD标准）

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI应用入口
│   │
│   ├── api/                             # 表现层（Presentation）
│   │   ├── __init__.py
│   │   ├── dependencies.py              # 依赖注入
│   │   ├── middleware.py                # 中间件
│   │   ├── v1/                          # API版本控制
│   │   │   ├── __init__.py
│   │   │   ├── endpoints/               # 端点
│   │   │   │   ├── __init__.py
│   │   │   │   ├── prices.py           # 价格端点
│   │   │   │   ├── fundamentals.py     # 基本面端点
│   │   │   │   ├── collectors.py       # 采集器端点
│   │   │   │   └── health.py           # 健康检查
│   │   │   └── router.py                # 路由聚合
│   │   └── websocket/                   # WebSocket
│   │       └── realtime.py
│   │
│   ├── application/                     # 应用层（Application）
│   │   ├── __init__.py
│   │   ├── dtos/                        # 数据传输对象
│   │   │   ├── __init__.py
│   │   │   ├── price_dto.py
│   │   │   ├── fundamental_dto.py
│   │   │   └── collector_dto.py
│   │   ├── use_cases/                   # 用例（业务流程）
│   │   │   ├── __init__.py
│   │   │   ├── collection/              # 采集相关用例
│   │   │   │   ├── __init__.py
│   │   │   │   ├── run_collector.py
│   │   │   │   ├── schedule_collection.py
│   │   │   │   └── stop_collector.py
│   │   │   ├── data_query/              # 查询相关用例
│   │   │   │   ├── __init__.py
│   │   │   │   ├── get_prices.py
│   │   │   │   ├── get_fundamentals.py
│   │   │   │   └── get_time_series.py
│   │   │   └── validation/              # 验证相关用例
│   │   │       ├── __init__.py
│   │   │       ├── validate_cross_source.py
│   │   │       └── detect_anomaly.py
│   │   ├── services/                    # 应用服务
│   │   │   ├── __init__.py
│   │   │   ├── collection_orchestrator.py
│   │   │   ├── data_aggregator.py
│   │   │   └── notification_service.py
│   │   └── commands/                    # 命令（CQRS模式，可选）
│   │       ├── __init__.py
│   │       └── start_collection_command.py
│   │
│   ├── domain/                          # 领域层（Domain）
│   │   ├── __init__.py
│   │   ├── market_data/                 # 市场数据领域
│   │   │   ├── __init__.py
│   │   │   ├── entities/                # 实体
│   │   │   │   ├── __init__.py
│   │   │   │   ├── price.py
│   │   │   │   ├── fundamental_indicator.py
│   │   │   │   └── futures_contract.py
│   │   │   ├── value_objects/           # 值对象
│   │   │   │   ├── __init__.py
│   │   │   │   ├── commodity.py
│   │   │   │   ├── location.py
│   │   │   │   ├── quality_score.py
│   │   │   │   └── time_range.py
│   │   │   ├── aggregates/              # 聚合根
│   │   │   │   ├── __init__.py
│   │   │   │   └── market_snapshot.py
│   │   │   ├── services/                # 领域服务
│   │   │   │   ├── __init__.py
│   │   │   │   ├── price_calculator.py
│   │   │   │   └── basis_calculator.py
│   │   │   ├── events/                  # 领域事件
│   │   │   │   ├── __init__.py
│   │   │   │   ├── price_updated.py
│   │   │   │   └── anomaly_detected.py
│   │   │   └── repositories/            # 仓储接口
│   │   │       ├── __init__.py
│   │   │       ├── price_repository.py
│   │   │       └── fundamental_repository.py
│   │   │
│   │   ├── collection/                  # 采集领域
│   │   │   ├── __init__.py
│   │   │   ├── entities/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── data_source.py
│   │   │   │   ├── collector.py
│   │   │   │   └── collection_task.py
│   │   │   ├── value_objects/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── source_type.py
│   │   │   │   ├── collection_status.py
│   │   │   │   └── reliability_tier.py
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── collector_factory.py
│   │   │   │   └── collection_scheduler.py
│   │   │   └── repositories/
│   │   │       ├── __init__.py
│   │   │       └── source_repository.py
│   │   │
│   │   └── validation/                  # 验证领域
│   │       ├── __init__.py
│   │       ├── entities/
│   │       │   └── validation_result.py
│   │       ├── services/
│   │       │   ├── __init__.py
│   │       │   ├── cross_source_validator.py
│   │       │   └── anomaly_detector.py
│   │       └── specifications/          # 规约模式
│   │           ├── __init__.py
│   │           └── quality_specification.py
│   │
│   ├── infrastructure/                  # 基础设施层（Infrastructure）
│   │   ├── __init__.py
│   │   ├── persistence/                 # 持久化
│   │   │   ├── __init__.py
│   │   │   ├── database.py              # 数据库连接
│   │   │   ├── models/                  # ORM模型
│   │   │   │   ├── __init__.py
│   │   │   │   ├── price_model.py
│   │   │   │   ├── fundamental_model.py
│   │   │   │   └── source_model.py
│   │   │   └── repositories/            # 仓储实现
│   │   │       ├── __init__.py
│   │   │       ├── sqlalchemy_price_repository.py
│   │   │       └── sqlalchemy_fundamental_repository.py
│   │   │
│   │   ├── collectors/                  # 采集器实现
│   │   │   ├── __init__.py
│   │   │   ├── base/
│   │   │   │   ├── __init__.py
│   │   │   │   └── base_collector.py
│   │   │   ├── official/                # 官方源
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dce_collector.py
│   │   │   │   └── nbs_collector.py
│   │   │   ├── commercial/              # 商业源
│   │   │   │   ├── __init__.py
│   │   │   │   └── mysteel_collector.py
│   │   │   └── public/                  # 公开源
│   │   │       ├── __init__.py
│   │   │       ├── boyar_collector.py
│   │   │       ├── sina_collector.py
│   │   │       └── netease_collector.py
│   │   │
│   │   ├── cache/                       # 缓存
│   │   │   ├── __init__.py
│   │   │   └── redis_cache.py
│   │   │
│   │   ├── messaging/                   # 消息队列（可选）
│   │   │   ├── __init__.py
│   │   │   └── event_bus.py
│   │   │
│   │   └── external/                    # 外部服务
│   │       ├── __init__.py
│   │       └── notification_provider.py
│   │
│   ├── shared/                          # 共享内核（Shared Kernel）
│   │   ├── __init__.py
│   │   ├── exceptions/                  # 自定义异常
│   │   │   ├── __init__.py
│   │   │   ├── domain_exceptions.py
│   │   │   └── infrastructure_exceptions.py
│   │   ├── utils/                       # 工具函数
│   │   │   ├── __init__.py
│   │   │   ├── datetime_utils.py
│   │   │   └── string_utils.py
│   │   └── constants/                   # 常量
│   │       ├── __init__.py
│   │       └── enums.py
│   │
│   └── config/                          # 配置
│       ├── __init__.py
│       ├── settings.py                  # 配置管理
│       └── logging.py                   # 日志配置
│
├── tests/                               # 测试
│   ├── __init__.py
│   ├── unit/                            # 单元测试
│   │   ├── domain/
│   │   └── application/
│   ├── integration/                     # 集成测试
│   │   ├── api/
│   │   └── infrastructure/
│   └── e2e/                             # 端到端测试
│
├── migrations/                          # 数据库迁移
│   └── versions/
│
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml                       # Python项目配置
└── README.md
```

---

## 三、核心设计原则

### 3.1 依赖倒置原则（DIP）

```python
# ✅ 正确：领域层定义接口，基础设施层实现

# domain/market_data/repositories/price_repository.py
from abc import ABC, abstractmethod

class PriceRepository(ABC):
    """价格仓储接口（领域层）"""
    
    @abstractmethod
    async def save(self, price: Price) -> None:
        pass
    
    @abstractmethod
    async def find_by_location_and_date(
        self, location: Location, date: datetime
    ) -> List[Price]:
        pass


# infrastructure/persistence/repositories/sqlalchemy_price_repository.py
class SQLAlchemyPriceRepository(PriceRepository):
    """价格仓储实现（基础设施层）"""
    
    async def save(self, price: Price) -> None:
        # 具体实现
        pass
    
    async def find_by_location_and_date(
        self, location: Location, date: datetime
    ) -> List[Price]:
        # 具体实现
        pass
```

### 3.2 聚合根模式

```python
# domain/market_data/aggregates/market_snapshot.py
class MarketSnapshot:
    """市场快照聚合根"""
    
    def __init__(self, date: datetime):
        self._date = date
        self._prices: List[Price] = []
        self._fundamentals: List[FundamentalIndicator] = []
        self._events: List[DomainEvent] = []
    
    def add_price(self, price: Price) -> None:
        """添加价格（业务规则在这里）"""
        if not self._validate_price(price):
            raise InvalidPriceException()
        
        self._prices.append(price)
        self._events.append(PriceAddedEvent(price))
    
    def _validate_price(self, price: Price) -> bool:
        # 业务规则：价格必须在合理范围内
        return 1000 <= price.value <= 5000
```

### 3.3 值对象

```python
# domain/market_data/value_objects/quality_score.py
from dataclasses import dataclass

@dataclass(frozen=True)  # 不可变
class QualityScore:
    """质量分数值对象"""
    
    value: float
    
    def __post_init__(self):
        if not 0 <= self.value <= 1:
            raise ValueError("Quality score must be between 0 and 1")
    
    @classmethod
    def from_factors(
        cls,
        source_tier: float,
        completeness: float,
        timeliness: float
    ) -> 'QualityScore':
        """从因子计算质量分数"""
        score = source_tier * completeness * timeliness
        return cls(round(score, 2))
    
    def is_high_quality(self) -> bool:
        """是否高质量"""
        return self.value >= 0.8
```

### 3.4 领域事件

```python
# domain/market_data/events/price_updated.py
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class PriceUpdatedEvent:
    """价格更新事件"""
    
    occurred_at: datetime
    commodity: str
    location: str
    old_price: float
    new_price: float
    
    @property
    def price_change(self) -> float:
        return self.new_price - self.old_price
    
    @property
    def price_change_percent(self) -> float:
        return (self.price_change / self.old_price) * 100
```

### 3.5 用例（Use Case）

```python
# application/use_cases/data_query/get_prices.py
from dataclasses import dataclass

@dataclass
class GetPricesRequest:
    """查询请求DTO"""
    location: str
    start_date: datetime
    end_date: datetime


@dataclass
class GetPricesResponse:
    """查询响应DTO"""
    prices: List[PriceDTO]
    total: int


class GetPricesUseCase:
    """获取价格用例"""
    
    def __init__(self, price_repository: PriceRepository):
        self._price_repository = price_repository
    
    async def execute(self, request: GetPricesRequest) -> GetPricesResponse:
        """执行用例"""
        # 1. 构建值对象
        location = Location(request.location)
        time_range = TimeRange(request.start_date, request.end_date)
        
        # 2. 调用领域层
        prices = await self._price_repository.find_by_location_and_time_range(
            location, time_range
        )
        
        # 3. 转换为DTO
        price_dtos = [PriceDTO.from_entity(p) for p in prices]
        
        return GetPricesResponse(
            prices=price_dtos,
            total=len(price_dtos)
        )
```

---

## 四、依赖注入

使用 `dependency-injector` 库实现DI容器：

```python
# api/dependencies.py
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    """DI容器"""
    
    # 配置
    config = providers.Configuration()
    
    # 基础设施
    database = providers.Singleton(
        Database,
        connection_string=config.database.url
    )
    
    redis_cache = providers.Singleton(
        RedisCache,
        url=config.redis.url
    )
    
    # 仓储
    price_repository = providers.Factory(
        SQLAlchemyPriceRepository,
        session_factory=database.provided.session
    )
    
    # 用例
    get_prices_use_case = providers.Factory(
        GetPricesUseCase,
        price_repository=price_repository
    )
```

---

## 五、关键优势

### vs 传统三层架构

| 特性 | 传统架构 | DDD架构 |
|------|---------|---------|
| 业务逻辑位置 | 分散在各层 | 集中在领域层 |
| 依赖方向 | 上层依赖下层 | 依赖倒置 |
| 可测试性 | 难以单元测试 | 易于测试 |
| 复杂度管理 | 业务复杂时失控 | 通过限界上下文管理 |
| 扩展性 | 耦合紧密 | 松耦合 |

### 维护性提升

1. **职责清晰**: 每层只关注自己的职责
2. **易于测试**: 领域层无外部依赖，纯业务逻辑
3. **易于扩展**: 新增功能只需添加新的用例
4. **易于重构**: 修改实现不影响领域层

---

## 六、实施步骤

### Phase 1: 核心领域建模（Week 1）
1. 识别聚合根
2. 定义实体和值对象
3. 定义仓储接口
4. 定义领域服务

### Phase 2: 应用层（Week 2）
1. 定义DTOs
2. 实现用例
3. 配置依赖注入

### Phase 3: 基础设施层（Week 3-4）
1. 实现仓储
2. 实现采集器
3. 实现缓存

### Phase 4: 表现层（Week 5-6）
1. FastAPI端点
2. WebSocket
3. 中间件

---

**这才是企业级标准架构**！准备好按DDD重新开始了吗？
