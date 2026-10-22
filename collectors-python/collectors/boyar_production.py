"""
博亚和讯采集器 - 生产版本
特性：
- Redis游标管理（增量采集）
- 限速和重试机制
- 原始HTML和执行日志存档
- 断点续传
"""
import re
import urllib.request
import urllib.error
import json
import os
import random
import socket
import tempfile
import time
from datetime import datetime, timezone
from typing import List, Optional
from pathlib import Path

import redis
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential

from config import BoyarConfig, configure_boyar_logging
from progress import report_progress
from .base import BaseCollector, RawDataRecord


def is_retryable(error):
    if isinstance(error, urllib.error.HTTPError):
        return error.code in (408, 429) or 500 <= error.code < 600
    return isinstance(error, (urllib.error.URLError, TimeoutError, ConnectionError, socket.timeout))


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
    
    def __init__(self, redis_client=None, data_dir="/app/data", config=None,
                 sleep=time.sleep, clock=time.monotonic, rng=None, log_dir=None):
        """
        初始化
        
        Args:
            redis_client: Redis客户端（可选，用于游标管理）
            data_dir: 数据存储目录
        """
        self.config = config or BoyarConfig()
        self.logger = configure_boyar_logging(self.config, log_dir)
        self.redis_client = redis_client if redis_client is not None else redis.Redis.from_url(
            self.config.redis_url, decode_responses=True,
            socket_connect_timeout=5, socket_timeout=5,
        )
        self.configure_cursor("boyar", redis_client=self.redis_client, key=self.config.cursor_key)
        self.data_dir = Path(data_dir)
        self.request_timeout = self.config.request_timeout
        self._sleep = sleep
        self._clock = clock
        self._rng = rng if rng is not None else random.Random()
        self._last_user_agent = None
        self.last_request_time = None
        self.stats = {}
    
    def collect(self, start_id: int = None, end_id: int = None, 
                incremental: bool = True, max_items: int = 100, **kwargs) -> List[RawDataRecord]:
        started = self._clock()
        self.stats = {"status": "running", "scanned": 0, "requests": 0,
                      "retries": 0, "archives": 0, "records": 0}
        self.logger.info("run_started incremental=%s start_id=%s end_id=%s max_items=%s",
                         incremental, start_id, end_id, max_items)
        try:
            records = self._collect(start_id, end_id, incremental, max_items)
            self.stats.update(status="success", records=len(records))
            return records
        except Exception:
            self.stats["status"] = "failed"
            self.logger.exception("run_failed; Redis checkpoint not committed")
            raise
        finally:
            self.stats["elapsed_seconds"] = round(self._clock() - started, 3)
            self.logger.info("run_finished %s", json.dumps(self.stats, ensure_ascii=False))

    def _collect(self, start_id, end_id, incremental, max_items):
        """
        采集博亚和讯山东到车数据
        
        Args:
            start_id: 起始文章ID（默认使用游标）
            end_id: 结束文章ID
            incremental: 是否增量采集
        """
        if max_items < 1 or (start_id is not None and start_id < 1):
            raise ValueError("max_items and start_id must be positive")
        if end_id is not None and end_id < 1:
            raise ValueError("end_id must be positive")
        # Serialize incremental runs across API workers; size the lease for the scan budget.
        attempts = self.config.max_retries + 1
        lock_ttl = int(self.config.scan_limit * (
            attempts * (self.request_timeout + self.config.max_interval) + 7
        ) + 60)
        if not incremental:
            return self._collect_batch(start_id, end_id, max_items, None)
        lock = self.cursor.lock(timeout=lock_ttl)
        if not lock.acquire(blocking=False):
            raise RuntimeError("Another Boyar incremental collection is running")
        try:
            last_id = self._last_article_id()
            self.stats["cursor_before"] = last_id
            records, checkpoint = self._scan(start_id, end_id, max_items, last_id)
            if checkpoint is not None:
                self._update_cursor(checkpoint)
            self.stats["cursor_after"] = checkpoint if checkpoint is not None else last_id
            return records
        finally:
            try:
                lock.release()
            except Exception as e:
                self.logger.warning("Failed to release lock: %s", e)

    def _collect_batch(self, start_id, end_id, max_items, last_id):
        records, _ = self._scan(start_id, end_id, max_items, last_id)
        return records

    def _scan(self, start_id, end_id, max_items, last_id):
        if start_id is None:
            start_id = last_id + 1 if last_id is not None else self.config.start_article_id
        if last_id is not None and start_id <= last_id:
            self.logger.info("Duplicate article %s already checkpointed at %s; stopping", start_id, last_id)
            return [], None
        stop_id = start_id + self.config.scan_limit - 1
        if end_id is not None:
            stop_id = min(stop_id, end_id)
        self.logger.info("Boyar scanning article IDs %s..%s", start_id, stop_id)
        records = []
        checkpoint = None
        scan_total = max(0, stop_id - start_id + 1)
        report_progress("scanning", 0, scan_total, records=0)
        for article_id in range(start_id, stop_id + 1):
            self.stats["scanned"] += 1
            try:
                article_data = self._fetch_article_with_retry(article_id)
            except urllib.error.HTTPError as error:
                if error.code in (404, 410):
                    # Do not checkpoint the not-yet-published frontier.
                    self.logger.info("Article %s unavailable (%s); stopping", article_id, error.code)
                    break
                raise
            if article_data:
                html_path = article_data['html_path']
                record = RawDataRecord(
                    business_date=article_data['date'],
                    collected_at=datetime.now(timezone.utc),
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
                        "html_path": html_path
                    }
                )
                records.append(record)
            # A successful non-target page is processed too, avoiding endless rescans.
            checkpoint = article_id
            report_progress("scanning", self.stats["scanned"], scan_total,
                            records=len(records), article_id=article_id)
            if len(records) >= max_items:
                break
        self.logger.info("Boyar collected %s records; checkpoint=%s", len(records), checkpoint)
        return records, checkpoint
    
    def _fetch_article_with_retry(self, article_id: int) -> Optional[dict]:
        """
        抓取单篇文章（带重试机制）
        
        Returns:
            dict | None: 成功返回数据，非目标文章返回None；请求失败抛出异常
        """
        def before_sleep(state):
            self.stats["retries"] = self.stats.get("retries", 0) + 1
            self.logger.warning("Article %s attempt %s failed: %s; retry in %.1fs",
                           article_id, state.attempt_number, state.outcome.exception(),
                           state.next_action.sleep)
        try:
            for attempt in Retrying(
                retry=retry_if_exception(is_retryable),
                stop=stop_after_attempt(self.config.max_retries + 1),
                wait=wait_exponential(multiplier=1, min=1, max=4),
                before_sleep=before_sleep, sleep=self._sleep, reraise=True,
            ):
                with attempt:
                    return self._fetch_article(article_id)
        except urllib.error.HTTPError as error:
            if error.code not in (404, 410):
                self.logger.exception("Article %s failed; batch checkpoint is unchanged", article_id)
            raise
        except Exception:
            self.logger.exception("Article %s failed; batch checkpoint is unchanged", article_id)
            raise
    
    def _fetch_article(self, article_id: int) -> Optional[dict]:
        """
        抓取单篇文章
        
        Returns:
            dict | None: {article_id, url, title, date, value, html} 或 None
        """
        url = f"{self.site_url}/article/{article_id}.html"
        
        self._rate_limit()
        agents = [a for a in self.config.user_agents if a != self._last_user_agent]
        self._last_user_agent = self._rng.choice(agents or self.config.user_agents)
        req = urllib.request.Request(url, headers={
            'User-Agent': self._last_user_agent,
            'Referer': self.site_url + '/',
        })
        self.stats["requests"] = self.stats.get("requests", 0) + 1
        with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
            html = resp.read().decode('utf-8', 'ignore')
        html_path = self._save_raw_html(article_id, html)
        
        # 提取标题中的日期
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        if not title_match:
            return None
        
        title = title_match.group(1).strip()
        
        # 提取日期 (格式: 2026年10月20日)
        date_match = re.search(r'(\d{4})年(\d+)月(\d+)日', title)
        if not date_match:
            return None
        
        year, month, day = map(int, date_match.groups())
        date_str = datetime(year, month, day).date().isoformat()
        
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
            'html': html,
            'html_path': html_path,
        }
    
    def _rate_limit(self):
        """限速控制"""
        interval = self._rng.uniform(self.config.min_interval, self.config.max_interval)
        # Delay the first request too, including across short-lived runner processes.
        elapsed = 0 if self.last_request_time is None else self._clock() - self.last_request_time
        remaining = interval - elapsed
        if remaining > 0:
            self._sleep(remaining)
        self.last_request_time = self._clock()
    
    def _save_raw_html(self, article_id: int, html: str):
        return self.save_html(article_id, html)

    def save_html(self, article_id: int, html: str):
        """
        保存原始HTML（UTF-8，原子写入）
        
        Args:
            article_id: 文章ID
            html: HTML内容
        """
        if not isinstance(article_id, int) or isinstance(article_id, bool) or article_id < 1:
            raise ValueError("article_id must be a positive integer")
        today = datetime.now().strftime('%Y-%m-%d')
        save_dir = self.data_dir / 'html' / 'boyar' / today
        save_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = save_dir / f"article_{article_id}.html"
        
        # Publish complete archives atomically, including when replaying a failed batch.
        fd, temp_path = tempfile.mkstemp(dir=save_dir, suffix='.tmp')
        os.close(fd)
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(html)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, file_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        self.stats["archives"] = self.stats.get("archives", 0) + 1
        self.logger.info("html_saved article_id=%s path=%s bytes=%s", article_id, file_path,
                         len(html.encode('utf-8')))
        return str(file_path)
    
    def _get_cursor(self) -> int:
        """
        从Redis获取游标（上次采集的最后ID）
        
        Returns:
            int: 上次采集的最后ID，如果没有则返回默认值
        """
        last_id = self._last_article_id()
        return last_id + 1 if last_id is not None else self.config.start_article_id

    def _last_article_id(self):
        return self.get_cursor()

    def _update_cursor(self, article_id: int):
        return self.advance_cursor(article_id)


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
