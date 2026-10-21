"""
新浪财经采集器

站点: https://finance.sina.com.cn
数据: 北港库存、下海量
"""
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List
from .base import BaseCollector, RawDataRecord


class SinaCollector(BaseCollector):
    """新浪财经采集器"""
    
    @property
    def collector_id(self) -> str:
        return "public_media_sina"
    
    @property
    def site_name(self) -> str:
        return "新浪财经"
    
    @property
    def site_url(self) -> str:
        return "https://finance.sina.com.cn"
    
    @property
    def source_type(self) -> str:
        return "public_media"
    
    def collect(self, **kwargs) -> List[RawDataRecord]:
        """采集新浪财经数据"""
        # TODO: 实现新浪财经采集逻辑
        return []


if __name__ == '__main__':
    collector = SinaCollector()
    records = collector.collect()
    print(f"采集到 {len(records)} 条记录")
