"""
采集器基类

定义所有采集器必须实现的接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class RawDataRecord:
    """原始数据记录"""
    business_date: str          # 业务日期 YYYY-MM-DD
    collected_at: datetime      # 采集时间
    published_at: Optional[datetime]  # 发布时间
    
    data_type: str             # arrivals/spot_price/inventory等
    indicator: str             # 指标名称
    value: float               # 数值
    unit: str                  # 单位
    region: str                # 地区
    
    source_url: str            # 来源URL
    original_text: Optional[str]  # 原文摘录
    metadata: Dict[str, Any]   # 元数据


class BaseCollector(ABC):
    """
    采集器基类
    
    每个站点必须继承这个类并实现抽象方法
    """
    
    @property
    @abstractmethod
    def collector_id(self) -> str:
        """采集器ID: {source_type}_{site_name}"""
        pass
    
    @property
    @abstractmethod
    def site_name(self) -> str:
        """站点名称"""
        pass
    
    @property
    @abstractmethod
    def site_url(self) -> str:
        """站点URL"""
        pass
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """
        来源类型:
        - official_government
        - official_exchange
        - commercial_primary
        - public_media
        - industry_portal
        """
        pass
    
    @abstractmethod
    def collect(self, **kwargs) -> List[RawDataRecord]:
        """
        执行采集
        
        Returns:
            List[RawDataRecord]: 原始数据记录列表
        """
        pass
    
    def configure_cursor(self, namespace, kind='int', **kwargs):
        from cursor import CursorManager
        self.cursor = CursorManager(namespace, kind, **kwargs)
        return self.cursor

    def get_cursor(self):
        cursor = getattr(self, 'cursor', None)
        return cursor.get() if cursor is not None else None

    def advance_cursor(self, value):
        cursor = getattr(self, 'cursor', None)
        if cursor is None:
            raise RuntimeError('Collector has no configured cursor')
        return cursor.advance(value)

    def validate_config(self) -> bool:
        """验证配置（可选覆盖）"""
        return True
