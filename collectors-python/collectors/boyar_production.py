"""
博亚和讯采集器 - 生产版本
特性：
- Redis游标管理（增量采集）
- 限速和重试机制
- 原始HTML保存（gzip压缩）
- 断点续传
"""
import re
import urllib.request
import urllib.error
import gzip
import hashlib
import time
import os
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from .base import BaseCollector, RawDataRecord


class BoyarProductionCollector(BaseCollector):
    """博亚和讯采集器 - 生产版本"""
    
    @property
    def collector_id(self) -> str:
        return "boyar_shandong_production"
    
    @property
    def site_name(self) -> str:
        return "博亚和讯"
    
    @property
    def site_url(self) -> str:
        return "https://m.boyar.cn"
    
    @property
    def source_type(self) -> str:
        return "commercial_primary"
    
    def __init__(self, redis_client=None, data_dir="/app/data"):
        """
        初始化
        
        Args:
            redis_client: Redis客户端（可选，用于游标管理）
            data_dir: 数据存储目录
        """
        self.redis_client = redis_client
        self.data_dir = Path(data_dir)
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
        }
        
        # 限速配置
        self.request_interval = 1.5  # 请求间隔（秒）
        self.request_timeout = 30    # 请求超时（秒）
        
        # 重试配置
        self.max_retries = 3
        self.retry_delays = [1, 2, 5]  # 重试延迟（秒）
        
        self.last_request_time = 0
    
    def collect(self, start_id: int = None, end_id: int = None, 
                incremental: bool = True, **kwargs) -> List[RawDataRecord]:
        """
        采集博亚和讯山东到车数据
        
        Args:
            start_id: 起始文章ID（默认使用游标）
            end_id: 结束文章ID
            incremental: 是否增量采集
        """
        print(f"[{self.collector_id}] 开始采集（生产模式）...")
        
        # 获取游标（上次采集的最后ID）
        if incremental and start_id is None:
            start_id = self._get_cursor()
            print(f"[{self.collector_id}] 增量采集，从ID {start_id} 开始")
        elif start_id is None:
            start_id = self._discover_latest_id()
            print(f"[{self.collector_id}] 全量采集，从ID {start_id} 开始")
        
        if end_id is None:
            end_id = start_id + 150
        
        print(f"[{self.collector_id}] 扫描范围: {start_id} - {end_id}")
        
        records = []
        found_count = 0
        error_count = 0
        
        for article_id in range(start_id, end_id + 1):
            # 限速
            self._rate_limit()
            
            # 抓取文章（带重试）
            article_data = self._fetch_article_with_retry(article_id)
            
            if article_data:
                # 保存原始HTML
                self._save_raw_html(article_id, article_data['html'])
                
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
                        "extraction_method": "regex_pattern",
                        "html_saved": True,
                        "html_path": article_data.get('html_path', '')
                    }
                )
                records.append(record)
                found_count += 1
                
                # 更新游标
                self._update_cursor(article_id)
                
                if found_count <= 3:
                    print(f"[{self.collector_id}]   ✓ {article_data['date']}: "
                          f"{article_data['value']} 台 (ID:{article_id})")
            elif article_data is False:  # 明确失败
                error_count += 1
                if error_count > 20:  # 连续失败过多，停止
                    print(f"[{self.collector_id}] ⚠ 连续失败{error_count}次，停止扫描")
                    break
        
        if records:
            print(f"[{self.collector_id}] ✓ 采集成功: {len(records)} 条数据")
        else:
            print(f"[{self.collector_id}] ⚠ 未找到有效数据")
        
        return records
    
    def _fetch_article_with_retry(self, article_id: int) -> Optional[dict]:
        """
        抓取单篇文章（带重试机制）
        
        Returns:
            dict | None | False: 成功返回dict，不存在返回None，失败返回False
        """
        for attempt in range(self.max_retries):
            try:
                result = self._fetch_article(article_id)
                return result
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    print(f"[{self.collector_id}] 文章{article_id}失败，{delay}秒后重试...")
                    time.sleep(delay)
                else:
                    print(f"[{self.collector_id}] 文章{article_id}失败（重试{self.max_retries}次）")
                    return False
        
        return False
    
    def _fetch_article(self, article_id: int) -> Optional[dict]:
        """
        抓取单篇文章
        
        Returns:
            dict | None: {article_id, url, title, date, value, html} 或 None
        """
        url = f"{self.site_url}/article/{article_id}.html"
        
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
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
            'value': value,
            'html': html
        }
    
    def _rate_limit(self):
        """限速控制"""
        now = time.time()
        elapsed = now - self.last_request_time
        
        if elapsed < self.request_interval:
            sleep_time = self.request_interval - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _save_raw_html(self, article_id: int, html: str):
        """
        保存原始HTML（gzip压缩）
        
        Args:
            article_id: 文章ID
            html: HTML内容
        """
        # 目录结构：data/raw/html/boyar/YYYY-MM-DD/
        today = datetime.now().strftime('%Y-%m-%d')
        save_dir = self.data_dir / 'raw' / 'html' / 'boyar' / today
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 文件名：{article_id}.html.gz
        file_path = save_dir / f"{article_id}.html.gz"
        
        # gzip压缩保存
        with gzip.open(file_path, 'wt', encoding='utf-8') as f:
            f.write(html)
        
        return str(file_path)
    
    def _get_cursor(self) -> int:
        """
        从Redis获取游标（上次采集的最后ID）
        
        Returns:
            int: 上次采集的最后ID，如果没有则返回默认值
        """
        if not self.redis_client:
            return self._discover_latest_id()
        
        try:
            cursor_key = f"collector:cursor:{self.collector_id}"
            cursor = self.redis_client.get(cursor_key)
            
            if cursor:
                last_id = int(cursor)
                # 从上次的下一个开始
                return last_id + 1
            else:
                return self._discover_latest_id()
        
        except Exception as e:
            print(f"[{self.collector_id}] Redis游标读取失败: {e}")
            return self._discover_latest_id()
    
    def _update_cursor(self, article_id: int):
        """
        更新Redis游标
        
        Args:
            article_id: 当前采集的文章ID
        """
        if not self.redis_client:
            return
        
        try:
            cursor_key = f"collector:cursor:{self.collector_id}"
            self.redis_client.set(cursor_key, article_id)
        except Exception as e:
            print(f"[{self.collector_id}] Redis游标更新失败: {e}")
    
    def _discover_latest_id(self) -> int:
        """
        智能发现最新的有效文章ID
        
        Returns:
            int: 建议的起始ID
        """
        # 已知的基准点（2026-10-08对应文章1267743）
        known_good_id = 1267743
        
        # 简化策略：假设每天约25篇文章
        days_passed = 13  # 从10-08到10-21
        estimated_new_articles = days_passed * 25
        
        test_id = known_good_id + estimated_new_articles
        
        # 快速测试
        if self._test_article_exists(test_id):
            print(f"[{self.collector_id}] 发现有效文章ID: {test_id}")
            return test_id - 300  # 往前扫描300篇
        
        return known_good_id + 100
    
    def _test_article_exists(self, article_id: int) -> bool:
        """快速测试文章是否存在"""
        url = f"{self.site_url}/article/{article_id}.html"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=1) as resp:
                return resp.status == 200
        except:
            return False


# 测试代码
if __name__ == "__main__":
    collector = BoyarProductionCollector(data_dir="./test_data")
    
    print("\n" + "="*60)
    print("博亚和讯采集器 - 生产版本测试")
    print("="*60 + "\n")
    
    # 测试增量采集
    records = collector.collect(start_id=1267700, end_id=1267750, incremental=False)
    
    if records:
        print(f"\n✓ 采集到 {len(records)} 条记录\n")
        print("详细数据:")
        print("-"*60)
        for i, r in enumerate(records[:10]):
            print(f"  {i+1:2}. {r.business_date} | {r.value:.0f} {r.unit}")
            print(f"      HTML已保存: {r.metadata.get('html_saved', False)}")
    else:
        print("\n⚠ 未找到数据")
