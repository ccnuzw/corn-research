"""
采集器模块

可用采集器：
- BoyarProductionCollector: 博亚和讯生产版（增量采集+限速+重试+HTML保存）
- SinaProductionCollector: 新浪财经生产版（多数据源+限速+重试）
- MockCollector: Mock数据采集器（测试用）
"""

from .base import BaseCollector, RawDataRecord
from .boyar_production import BoyarProductionCollector
from .sina_production import SinaProductionCollector
from .dce_production import DceProductionCollector
from .mock import MockCollector

__all__ = [
    'BaseCollector',
    'RawDataRecord',
    'BoyarProductionCollector',
    'SinaProductionCollector',
    'DceProductionCollector',
    'MockCollector',
]
