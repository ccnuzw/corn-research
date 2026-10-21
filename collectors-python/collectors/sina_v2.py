"""
新浪财经采集器 - V2版本
数据源: 新浪财经转引Mysteel北方四港周报
采集: 北方四港库存、下海量
"""
import re
import urllib.request
import urllib.error
from datetime import datetime
from typing import List, Optional
import json

from .base import BaseCollector, RawDataRecord


class SinaCollectorV2(BaseCollector):
    """新浪财经采集器 V2 - 北方四港周报"""
    
    @property
    def collector_id(self) -> str:
        return "sina_north_port"
    
    @property
    def site_name(self) -> str:
        return "新浪财经"
    
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
        # 新浪财经玉米相关关键词
        self.search_keywords = ['北方四港', '玉米库存', 'Mysteel', '北港']
    
    def collect(self, **kwargs) -> List[RawDataRecord]:
        """
        采集新浪财经北方四港数据
        
        策略：使用旧项目验证过的URL模式
        """
        print(f"[{self.collector_id}] 开始采集新浪财经北港数据...")
        
        records = []
        
        # 使用多个可能的URL（新浪财经文章URL格式）
        test_urls = [
            # 2026年10月的可能URL
            "https://finance.sina.com.cn/futuremarket/2026-10-07/doc-incikqex.shtml",
            "https://finance.sina.com.cn/futuremarket/2026-10-14/doc-incikqex.shtml",
            "https://finance.sina.com.cn/roll/2026-10-07/doc-incikqex.shtml",
        ]
        
        for url in test_urls:
            article_data = self._fetch_article(url)
            
            if article_data:
                print(f"[{self.collector_id}] ✓ 找到有效文章: {url}")
                
                # 提取库存数据
                inventory_records = self._extract_inventory(article_data)
                records.extend(inventory_records)
                
                # 提取下海量数据
                shipping_records = self._extract_shipping(article_data)
                records.extend(shipping_records)
                
                break  # 找到一个就够了
        
        if records:
            print(f"[{self.collector_id}] ✓ 采集成功: {len(records)} 条数据")
            for i, r in enumerate(records[:3]):
                print(f"[{self.collector_id}]   [{i+1}] {r.indicator}: {r.value} {r.unit}")
        else:
            print(f"[{self.collector_id}] ⚠ 未找到有效数据，URL可能过期")
            print(f"[{self.collector_id}] 提示：需要手动更新最新的新浪财经文章URL")
        
        return records
    
    def _fetch_article(self, url: str) -> Optional[dict]:
        """
        抓取文章内容
        
        Returns:
            dict | None: {url, title, content, date} 或 None
        """
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
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
            
            # 提取正文内容
            # 新浪财经文章主体通常在 article 标签或特定 div 中
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
        
        except (urllib.error.HTTPError, urllib.error.URLError):
            return None
        except Exception as e:
            print(f"[{self.collector_id}] 抓取失败: {e}")
            return None
    
    def _extract_inventory(self, article: dict) -> List[RawDataRecord]:
        """提取库存数据"""
        records = []
        content = article['content']
        
        # 模式：北方四港库存 XXX万吨
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
        
        # 模式：周度下海量 XXX万吨
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


# 测试代码
if __name__ == "__main__":
    collector = SinaCollectorV2()
    
    print("\n" + "="*60)
    print("新浪财经采集器 V2 测试")
    print("="*60 + "\n")
    
    records = collector.collect()
    
    if records:
        print(f"\n✓ 采集到 {len(records)} 条记录\n")
        print("详细数据:")
        print("-"*60)
        for i, r in enumerate(records):
            print(f"  {i+1}. {r.business_date} | {r.indicator}: {r.value} {r.unit}")
            print(f"     原文: {r.original_text[:50]}...")
    else:
        print("\n⚠ 未找到数据")
        print("提示: 需要找到最新的新浪财经玉米文章URL")
