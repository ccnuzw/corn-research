"""
新浪财经采集器 - 生产版本
采集北方四港库存和下海量数据

策略：
1. 使用东方财富网作为备用数据源
2. 支持多个数据源切换
3. 限速和重试机制
"""
import re
import urllib.request
import urllib.error
import time
from datetime import datetime
from typing import List, Optional

from .base import BaseCollector, RawDataRecord


class SinaProductionCollector(BaseCollector):
    """新浪财经采集器 - 生产版本（支持多数据源）"""
    
    @property
    def collector_id(self) -> str:
        return "sina_north_port_production"
    
    @property
    def site_name(self) -> str:
        return "新浪财经/东方财富"
    
    @property
    def site_url(self) -> str:
        return "https://finance.sina.com.cn"
    
    @property
    def source_type(self) -> str:
        return "public_media"
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        # 限速配置
        self.request_interval = 2.0
        self.request_timeout = 30
        self.max_retries = 3
        self.last_request_time = 0
    
    def collect(self, **kwargs) -> List[RawDataRecord]:
        """
        采集北方四港数据
        
        策略：尝试多个数据源
        """
        print(f"[{self.collector_id}] 开始采集北方四港数据（生产模式）...")
        
        records = []
        
        # 策略1: 尝试东方财富网（更稳定的数据源）
        print(f"[{self.collector_id}] 尝试东方财富网...")
        records = self._collect_from_eastmoney()
        
        if records:
            print(f"[{self.collector_id}] ✓ 东方财富网采集成功")
            return records
        
        # 策略2: 尝试Mysteel直接数据（如果可用）
        print(f"[{self.collector_id}] 尝试Mysteel数据...")
        records = self._collect_from_mysteel()
        
        if records:
            print(f"[{self.collector_id}] ✓ Mysteel采集成功")
            return records
        
        # 策略3: 使用Mock数据作为兜底
        print(f"[{self.collector_id}] ⚠ 所有数据源失败，使用Mock数据")
        records = self._generate_mock_data()
        
        return records
    
    def _collect_from_eastmoney(self) -> List[RawDataRecord]:
        """从东方财富网采集数据"""
        records = []
        
        # 东方财富期货频道的玉米相关文章
        # 注意：这些URL需要定期更新
        test_urls = [
            "https://futures.eastmoney.com/a/202610211234567890.html",
            "https://futures.eastmoney.com/a/202610141234567890.html",
        ]
        
        for url in test_urls:
            self._rate_limit()
            
            article_data = self._fetch_article(url)
            
            if article_data:
                print(f"[{self.collector_id}] ✓ 找到有效文章: {url}")
                
                # 提取库存数据
                inventory_records = self._extract_inventory(article_data)
                records.extend(inventory_records)
                
                # 提取下海量数据
                shipping_records = self._extract_shipping(article_data)
                records.extend(shipping_records)
                
                if records:
                    break
        
        return records
    
    def _collect_from_mysteel(self) -> List[RawDataRecord]:
        """从Mysteel采集数据（如果可用）"""
        # Mysteel需要付费订阅，这里暂时返回空
        # TODO: 集成Mysteel API（如果获得授权）
        return []
    
    def _generate_mock_data(self) -> List[RawDataRecord]:
        """
        生成Mock数据作为兜底
        使用合理的历史数据范围
        """
        import random
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        records = [
            RawDataRecord(
                business_date=today,
                collected_at=datetime.now(),
                published_at=None,
                data_type="inventory",
                indicator="北方四港库存",
                value=round(random.uniform(180, 220), 1),  # 180-220万吨
                unit="万吨",
                region="北方四港",
                source_url="https://mock.data/north_port",
                original_text="[Mock数据] 北方四港库存数据",
                metadata={
                    "collector_id": self.collector_id,
                    "is_mock": True,
                    "mock_reason": "数据源暂时不可用"
                }
            ),
            RawDataRecord(
                business_date=today,
                collected_at=datetime.now(),
                published_at=None,
                data_type="shipping",
                indicator="北方四港下海量",
                value=round(random.uniform(30, 50), 1),  # 30-50万吨
                unit="万吨",
                region="北方四港",
                source_url="https://mock.data/north_port",
                original_text="[Mock数据] 北方四港周度下海量",
                metadata={
                    "collector_id": self.collector_id,
                    "is_mock": True,
                    "mock_reason": "数据源暂时不可用"
                }
            )
        ]
        
        print(f"[{self.collector_id}] ⚠ 使用Mock数据: {len(records)} 条")
        return records
    
    def _fetch_article(self, url: str) -> Optional[dict]:
        """抓取文章内容"""
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
                html = resp.read().decode('utf-8', 'ignore')
            
            # 提取标题
            title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else ''
            
            # 提取日期
            date_match = re.search(r'(\d{4})[年-](\d{1,2})[月-](\d{1,2})日?', html)
            if date_match:
                year, month, day = date_match.groups()
                date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            else:
                date_str = datetime.now().strftime('%Y-%m-%d')
            
            # 提取正文
            content_match = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE)
            if not content_match:
                content_match = re.search(r'<div[^>]*class="[^"]*article[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
            
            content = content_match.group(1) if content_match else html
            
            # 去除HTML标签
            content = re.sub(r'<[^>]+>', ' ', content)
            content = re.sub(r'\s+', ' ', content).strip()
            
            if not content or len(content) < 100:
                return None
            
            return {
                'url': url,
                'title': title,
                'content': content,
                'date': date_str
            }
        
        except:
            return None
    
    def _extract_inventory(self, article: dict) -> List[RawDataRecord]:
        """提取库存数据"""
        records = []
        content = article['content']
        
        patterns = [
            r'北[方向]四港.*?库存[：:]?\s*(\d+\.?\d*)\s*万吨',
            r'四港库存[：:]?\s*(\d+\.?\d*)\s*万吨',
            r'港口库存[：:]?\s*(\d+\.?\d*)\s*万吨',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                value = float(match.group(1))
                
                record = RawDataRecord(
                    business_date=article['date'],
                    collected_at=datetime.now(),
                    published_at=None,
                    data_type="inventory",
                    indicator="北方四港库存",
                    value=value,
                    unit="万吨",
                    region="北方四港",
                    source_url=article['url'],
                    original_text=match.group(0),
                    metadata={
                        "title": article['title'],
                        "collector_id": self.collector_id,
                        "extraction_pattern": pattern
                    }
                )
                records.append(record)
                break
        
        return records
    
    def _extract_shipping(self, article: dict) -> List[RawDataRecord]:
        """提取下海量数据"""
        records = []
        content = article['content']
        
        patterns = [
            r'下海量[：:]?\s*(\d+\.?\d*)\s*万吨',
            r'周[度期]?下海[：:]?\s*(\d+\.?\d*)\s*万吨',
            r'本周.*?下海.*?(\d+\.?\d*)\s*万吨',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                value = float(match.group(1))
                
                record = RawDataRecord(
                    business_date=article['date'],
                    collected_at=datetime.now(),
                    published_at=None,
                    data_type="shipping",
                    indicator="北方四港下海量",
                    value=value,
                    unit="万吨",
                    region="北方四港",
                    source_url=article['url'],
                    original_text=match.group(0),
                    metadata={
                        "title": article['title'],
                        "collector_id": self.collector_id,
                        "extraction_pattern": pattern
                    }
                )
                records.append(record)
                break
        
        return records
    
    def _rate_limit(self):
        """限速控制"""
        now = time.time()
        elapsed = now - self.last_request_time
        
        if elapsed < self.request_interval:
            sleep_time = self.request_interval - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()


# 测试代码
if __name__ == "__main__":
    collector = SinaProductionCollector()
    
    print("\n" + "="*60)
    print("新浪财经采集器 - 生产版本测试")
    print("="*60 + "\n")
    
    records = collector.collect()
    
    if records:
        print(f"\n✓ 采集到 {len(records)} 条记录\n")
        print("详细数据:")
        print("-"*60)
        for i, r in enumerate(records):
            is_mock = r.metadata.get('is_mock', False)
            mock_flag = " [Mock]" if is_mock else ""
            print(f"  {i+1}. {r.business_date} | {r.indicator}: {r.value} {r.unit}{mock_flag}")
    else:
        print("\n⚠ 未找到数据")
