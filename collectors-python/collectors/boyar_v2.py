"""
博亚和讯采集器 - V2版本
基于旧项目的成功经验重写
数据源: https://m.boyar.cn
"""
import re
import urllib.request
import urllib.error
from datetime import datetime
from typing import List, Optional

from .base import BaseCollector, RawDataRecord


class BoyarCollectorV2(BaseCollector):
    """博亚和讯采集器 V2 - 基于实战验证的版本"""
    
    @property
    def collector_id(self) -> str:
        return "boyar_shandong_v2"
    
    @property
    def site_name(self) -> str:
        return "博亚和讯"
    
    @property
    def site_url(self) -> str:
        return "https://m.boyar.cn"
    
    @property
    def source_type(self) -> str:
        return "commercial_primary"
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
        }
    
    def collect(self, start_id: int = None, end_id: int = None, **kwargs) -> List[RawDataRecord]:
        """
        采集博亚和讯山东到车数据
        
        Args:
            start_id: 起始文章ID（默认使用智能发现）
            end_id: 结束文章ID
        """
        # 智能发现最新文章ID范围
        if start_id is None:
            start_id = self._discover_latest_id()
            print(f"[{self.collector_id}] 智能发现起始ID: {start_id}")
        
        if end_id is None:
            end_id = start_id + 150  # 扫描150篇文章，提高命中率
        
        print(f"[{self.collector_id}] 开始采集博亚和讯数据...")
        print(f"[{self.collector_id}] 扫描文章ID: {start_id} - {end_id}")
        
        records = []
        found_count = 0
        
        for article_id in range(start_id, end_id + 1):
            article_data = self._fetch_article(article_id)
            
            if article_data:
                # 转换为RawDataRecord
                record = RawDataRecord(
                    business_date=article_data['date'],
                    collected_at=datetime.now(),
                    published_at=None,
                    data_type="arrivals",
                    indicator="山东深加工到车量",
                    value=float(article_data['value']),
                    unit="台",
                    region="山东",
                    source_url=article_data['url'],
                    original_text=article_data['title'],
                    metadata={
                        "article_id": article_id,
                        "collector_id": self.collector_id,
                        "extraction_method": "regex_pattern"
                    }
                )
                records.append(record)
                found_count += 1
                
                if found_count <= 3:
                    print(f"[{self.collector_id}]   ✓ {article_data['date']}: {article_data['value']} 台 (文章{article_id})")
        
        if records:
            print(f"[{self.collector_id}] ✓ 采集成功: {len(records)} 条数据")
        else:
            print(f"[{self.collector_id}] ⚠ 未找到有效数据 (扫描范围 {start_id}-{end_id})")
        
        return records
    
    def _fetch_article(self, article_id: int) -> Optional[dict]:
        """
        抓取单篇文章
        
        Returns:
            dict | None: {article_id, url, title, date, value} 或 None
        """
        url = f"{self.site_url}/article/{article_id}.html"
        
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                html = resp.read().decode('utf-8', 'ignore')
            
            # 提取标题中的日期
            title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
            if not title_match:
                return None
            
            title = title_match.group(1).strip()
            
            # 提取日期 (格式: 2026年10月20日)
            date_match = re.search(r'2026年(\d+)月(\d+)日', title)
            if not date_match:
                return None
            
            month = date_match.group(1).zfill(2)
            day = date_match.group(2).zfill(2)
            date_str = f"2026-{month}-{day}"
            
            # 检查是否包含山东到货数据
            if '山东' not in html or ('到货' not in html and '到车' not in html):
                return None
            
            # 提取数值（多种模式）
            patterns = [
                r'山东深加工企业晨间到车辆?(\d{1,4})[车台]',
                r'晨间到车辆?(\d{1,4})[车台]',
                r'山东.*?到[货车].*?(\d{1,4})[车台]',
            ]
            
            value = None
            for pattern in patterns:
                match = re.search(pattern, html)
                if match:
                    val = int(match.group(1))
                    # 合理范围检查 (100-2000台)
                    if 100 <= val <= 2000:
                        value = val
                        break
            
            if not value:
                return None
            
            return {
                'article_id': article_id,
                'url': url,
                'title': title,
                'date': date_str,
                'value': value
            }
        
        except (urllib.error.HTTPError, urllib.error.URLError):
            return None
        except Exception:
            return None
    
    def _discover_latest_id(self) -> int:
        """
        智能发现最新的有效文章ID（快速版本）
        
        Returns:
            int: 建议的起始ID
        """
        # 已知的基准点（2026-10-08对应文章1267743）
        known_good_id = 1267743
        
        # 简化策略：假设每天约25篇文章
        # 但博亚不是每天都发山东到车，所以往回多扫描
        days_passed = 13  # 从10-08到10-21
        estimated_new_articles = days_passed * 25  # 约325篇
        
        test_id = known_good_id + estimated_new_articles
        
        # 快速测试（只测试1个点，超时1秒）
        if self._test_article_exists(test_id):
            print(f"[{self.collector_id}] 发现有效文章ID: {test_id}")
            # 往回扫描更多，因为山东到车不是每天都有
            return test_id - 300  # 往前扫描300篇，覆盖约12天
        
        # 如果失败，从已知点往后200篇开始
        return known_good_id + 100  # 保守策略
    
    def _test_article_exists(self, article_id: int) -> bool:
        """快速测试文章是否存在（不解析内容）"""
        url = f"{self.site_url}/article/{article_id}.html"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=1) as resp:  # 超时1秒
                return resp.status == 200
        except:
            return False


# 测试代码
if __name__ == "__main__":
    collector = BoyarCollectorV2()
    
    print("\n" + "="*60)
    print("博亚和讯采集器 V2 测试")
    print("="*60 + "\n")
    
    # 测试最近的文章ID范围
    records = collector.collect(start_id=1267700, end_id=1267750)
    
    if records:
        print(f"\n✓ 采集到 {len(records)} 条记录\n")
        print("详细数据:")
        print("-"*60)
        for i, r in enumerate(records[:10]):
            print(f"  {i+1:2}. {r.business_date} | {r.value:.0f} {r.unit} | 文章{r.metadata['article_id']}")
    else:
        print("\n⚠ 未找到数据，尝试调整文章ID范围")
        print("提示: 可以使用 start_id 和 end_id 参数指定范围")
