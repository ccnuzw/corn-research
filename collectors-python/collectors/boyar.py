"""
博亚和讯采集器

站点: https://m.boyar.cn
数据: 山东到车、价格、开机率
"""
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Optional
from .base import BaseCollector, RawDataRecord


class BoyarCollector(BaseCollector):
    """博亚和讯采集器"""
    
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
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'
        })
    
    def collect(self, start_id: int = 1267500, end_id: int = 1267600) -> List[RawDataRecord]:
        """
        采集博亚和讯文章
        
        Args:
            start_id: 起始文章ID
            end_id: 结束文章ID
        """
        records = []
        
        for article_id in range(start_id, end_id + 1):
            try:
                article_records = self._fetch_article(article_id)
                records.extend(article_records)
            except Exception as e:
                print(f"Failed to fetch article {article_id}: {e}")
                continue
        
        return records
    
    def _fetch_article(self, article_id: int) -> List[RawDataRecord]:
        """获取单篇文章"""
        url = f"{self.site_url}/article/{article_id}.html"
        
        response = self.session.get(url, timeout=self.timeout)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取标题
        title_elem = soup.select_one('h1.title')
        title = title_elem.text.strip() if title_elem else ''
        
        # 提取正文
        content_elem = soup.select_one('.article-body')
        content = content_elem.text if content_elem else ''
        
        # 提取数据
        records = []
        records.extend(self._extract_arrivals(content, url, title))
        
        return records
    
    def _extract_arrivals(self, content: str, url: str, title: str) -> List[RawDataRecord]:
        """提取到车量数据"""
        records = []
        
        # 规则: X月X日.*山东.*到车.*数字
        pattern = r'(\d{1,2})月(\d{1,2})日.*?山东.*?到车.*?(\d+)'
        
        for match in re.finditer(pattern, content):
            month = int(match.group(1))
            day = int(match.group(2))
            value = float(match.group(3))
            
            # 推断年份
            now = datetime.now()
            year = now.year
            if month > now.month:
                year -= 1
            
            business_date = f"{year}-{month:02d}-{day:02d}"
            
            # 从URL提取article_id
            article_id = url.split('/')[-1].replace('.html', '')
            
            record = RawDataRecord(
                business_date=business_date,
                collected_at=datetime.now(),
                published_at=None,  # TODO: 提取发布时间
                data_type='arrivals',
                indicator='山东深加工到车量',
                value=value,
                unit='台',
                region='山东',
                source_url=url,
                original_text=match.group(0),
                metadata={
                    'title': title,
                    'article_id': article_id,
                    'extraction_rule': 'pattern1'
                }
            )
            
            records.append(record)
        
        return records


if __name__ == '__main__':
    # 测试
    collector = BoyarCollector()
    records = collector.collect(start_id=1267650, end_id=1267660)
    
    print(f"采集到 {len(records)} 条记录")
    for r in records[:3]:
        print(f"  {r.business_date}: {r.indicator} = {r.value}{r.unit}")
