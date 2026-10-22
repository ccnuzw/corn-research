"""Official DCE daily corn settlements/closing prices; no synthetic fallback."""
import hashlib
import json
import logging
import math
import os
import random
import re
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential

from config import BoyarConfig
from progress import report_progress
from .base import BaseCollector, RawDataRecord

logger = logging.getLogger(__name__)


class DceSourceError(RuntimeError):
    pass


class DceProductionCollector(BaseCollector):
    collector_id = "dce_production"
    site_name = "大连商品交易所"
    site_url = "http://www.dce.com.cn/publicweb/quotesdata/dayQuotesCh.html"
    source_name = site_name
    source_url = site_url
    source_type = "official_exchange"
    # The supplied URL is a web page, not a JSON API. Current daily statistics API:
    api_url = "http://www.dce.com.cn/dcereport/publicweb/dailystat/dayQuotes"

    def __init__(self, *, opener=None, sleep=None, uniform=None, now=None,
                 redis_client=None, cursor_key=None, contracts=None, start_date=None,
                 max_days=None):
        self._opener = opener or urllib.request.urlopen
        self._sleep = sleep or time.sleep
        self._uniform = uniform or random.uniform
        self._now = now or (lambda: datetime.now(ZoneInfo("Asia/Shanghai")))
        names = contracts if contracts is not None else os.getenv("DCE_CONTRACTS", "")
        if isinstance(names, str):
            names = [s.strip() for s in names.split(",") if s.strip()]
        self.contracts = tuple(sorted(set(self._contract(s) for s in names)))
        # Changing the contract subset must not inherit an all-contract checkpoint.
        scope = hashlib.sha256(",".join(self.contracts).encode()).hexdigest()[:16] if self.contracts else None
        key = cursor_key or os.getenv("DCE_CURSOR_KEY") or "collector:dce:last_date"
        if scope:
            key += ":contracts:" + scope
        self.configure_cursor("dce", "date", redis_client=redis_client, key=key)
        self.start_date = self._date(start_date or os.getenv("DCE_START_DATE"))
        self.max_days = max_days if max_days is not None else int(os.getenv("DCE_MAX_DAYS", "31"))
        if isinstance(self.max_days, bool) or not isinstance(self.max_days, int) or not 1 <= self.max_days <= 366:
            raise ValueError("DCE_MAX_DAYS must be 1..366 calendar days")
        self.request_timeout = 30
        self.max_retries = 3
        self.user_agents = BoyarConfig.user_agents
        self._ua_index = random.randrange(len(self.user_agents))

    @staticmethod
    def _contract(value):
        if not isinstance(value, str) or not re.fullmatch(r"[cC]\d{2}(?:0[1-9]|1[0-2])", value):
            raise ValueError("Expected a corn contract such as C2701: " + str(value))
        return value.upper()

    @staticmethod
    def _date(value):
        if value is None:
            return None
        if not isinstance(value, str) or not re.fullmatch(r"(?:\d{4}-\d{2}-\d{2}|\d{8})", value):
            raise ValueError("Expected YYYY-MM-DD or YYYYMMDD: " + str(value))
        return date.fromisoformat(value)

    @staticmethod
    def _number(value, *, optional=False, integer=False):
        if optional and (value is None or isinstance(value, str) and value.strip() in ("", "-", "--")):
            return None
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise DceSourceError("Invalid DCE numeric field: " + repr(value))
        text = str(value).strip()
        if not re.fullmatch(r"[+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", text):
            raise DceSourceError("Invalid DCE numeric field: " + text)
        number = float(text.replace(",", ""))
        if not math.isfinite(number) or number < 0 or integer and not number.is_integer():
            raise DceSourceError("Invalid DCE numeric field: " + text)
        return int(number) if integer else number

    @staticmethod
    def _retryable(exc):
        if isinstance(exc, urllib.error.HTTPError):
            return exc.code in (408, 429) or 500 <= exc.code < 600
        return isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError))

    def _fetch_day(self, day):
        payload = {"contractId": "", "lang": "zh", "optionSeries": "", "statisticsType": "0",
                   "tradeDate": day.strftime("%Y%m%d"), "tradeType": "1", "varietyId": "all"}
        for attempt in Retrying(stop=stop_after_attempt(self.max_retries + 1),
                wait=wait_exponential(multiplier=1, min=1, max=4), sleep=self._sleep,
                retry=retry_if_exception(self._retryable), reraise=True):
            with attempt:
                self._sleep(self._uniform(1, 3))
                ua = self.user_agents[self._ua_index % len(self.user_agents)]
                self._ua_index += 1
                request = urllib.request.Request(self.api_url, data=json.dumps(payload).encode(),
                    headers={"Content-Type": "application/json", "Accept": "application/json",
                             "User-Agent": ua, "Referer": self.site_url}, method="POST")
                try:
                    with self._opener(request, timeout=self.request_timeout) as response:
                        raw = response.read(8 * 1024 * 1024 + 1)
                    if len(raw) > 8 * 1024 * 1024:
                        raise DceSourceError("DCE response exceeds 8 MiB limit")
                    result = json.loads(raw.decode("utf-8-sig"))
                    logger.info("dce_fetched date=%s bytes=%d attempt=%d", day, len(raw),
                                attempt.retry_state.attempt_number)
                    return result
                except (ValueError, UnicodeError) as exc:
                    raise DceSourceError("DCE returned non-JSON data (possible access challenge); no fallback") from exc
                except Exception as exc:
                    logger.warning("dce_request_failed date=%s attempt=%d error=%s", day,
                                   attempt.retry_state.attempt_number, exc)
                    raise

    def _parse_day(self, payload, day):
        if (not isinstance(payload, dict) or payload.get("success") is False
                or ("code" in payload and str(payload["code"]) not in ("0", "200", "0000", "000000"))
                or not isinstance(payload.get("data"), list)):
            raise DceSourceError("Unexpected DCE response envelope or unsuccessful response")
        if payload.get("tradeDate") is not None and self._date(payload["tradeDate"]) != day:
            raise DceSourceError("DCE response date differs from requested date")
        records = {}
        for row in payload["data"]:
            if not isinstance(row, dict):
                raise DceSourceError("DCE daily row is not an object")
            variety, contract = row.get("variety", ""), row.get("contractId", "")
            if not isinstance(variety, str) or not isinstance(contract, str):
                raise DceSourceError("Invalid DCE variety/contract field")
            if any(label in variety for label in ("小计", "总计", "合计")):
                continue
            if variety.strip() != "玉米" and not re.fullmatch(r"[cC]\d{4}", contract):
                continue
            if variety.strip() not in ("", "玉米"):
                raise DceSourceError("Corn contract has inconsistent variety: " + variety)
            try:
                contract = self._contract(contract)
            except ValueError as exc:
                raise DceSourceError(str(exc)) from exc
            if self.contracts and contract not in self.contracts:
                continue
            if contract in records:
                raise DceSourceError("Duplicate DCE contract: " + contract)
            if row.get("tradeDate") is not None and self._date(row["tradeDate"]) != day:
                raise DceSourceError("DCE row date differs from requested date")
            prices = {name: self._number(row.get(name), optional=True)
                      for name in ("open", "high", "low", "close", "lastClear", "clearPrice")}
            volume = self._number(row.get("volumn"), optional=True, integer=True)
            interest = self._number(row.get("openInterest"), optional=True, integer=True)
            field = "close" if prices["close"] is not None and prices["close"] > 0 else "clearPrice"
            value = prices[field]
            if value is None or value <= 0:
                raise DceSourceError("Corn contract has no positive close/settlement: " + contract)
            if prices["low"] and prices["high"] and prices["low"] > prices["high"]:
                raise DceSourceError("DCE low exceeds high: " + contract)
            records[contract] = RawDataRecord(
                business_date=day.isoformat(), collected_at=datetime.now(timezone.utc), published_at=None,
                data_type="futures_price", indicator="玉米期货价格", value=value, unit="元/吨",
                region=self.site_name, source_url=self.api_url,
                original_text=json.dumps(row, ensure_ascii=False, sort_keys=True),
                metadata={"collector_id": self.collector_id, "topic_name": "corn_futures_price",
                    "exchange": "DCE", "contract": contract, "record_key": contract,
                    "is_mock": False, "quality_grade": "A", "price_field": field,
                    "prices": prices, "volume": volume, "open_interest": interest,
                    "business_date_origin": "official_daily_query.tradeDate",
                    "request_trade_date": day.strftime("%Y%m%d"), "continuous": False})
        # All contracts are returned, not guessed dominant contracts or expired hardcoded symbols.
        return [records[key] for key in sorted(records)]

    def _latest_completed_day(self):
        now = self._now()
        if now.tzinfo is None:
            raise ValueError("DCE clock must be timezone-aware")
        now = now.astimezone(ZoneInfo("Asia/Shanghai"))
        # Avoid checkpointing an incomplete same-day publication before evening.
        return now.date() if now.hour >= 18 else now.date() - timedelta(days=1)

    def collect(self, max_items=100, incremental=True, *, start_date=None, end_date=None, **kwargs):
        if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 1:
            raise ValueError("max_items must be a positive integer")
        end = self._date(end_date) or self._latest_completed_day()
        if end > self._latest_completed_day():
            raise ValueError("DCE end_date must not exceed latest completed publication day")
        start = self._date(start_date) or self.start_date
        if start and start > end:
            raise ValueError("DCE start_date must not exceed end_date")
        lock = self.cursor.lock(timeout=7200) if incremental else None
        if lock and not lock.acquire(blocking=False):
            raise RuntimeError("Another DCE incremental collection is running")
        try:
            last = self._date(self.get_cursor()) if incremental else None
            if last:
                start = max(start or last + timedelta(days=1), last + timedelta(days=1))
            if start and start > end:
                return []
            # Bootstrap the latest available day with bounded holiday lookback.
            bootstrap = start is None
            if bootstrap:
                days = [end - timedelta(days=i) for i in range(14)]
            else:
                count = min((end - start).days + 1, self.max_days)
                days = [start + timedelta(days=i) for i in range(count)]
            records, checkpoint, observed = [], None, False
            for i, day in enumerate(days):
                if day.weekday() >= 5:
                    continue
                rows = self._parse_day(self._fetch_day(day), day)
                report_progress("scanning", i + 1, len(days), trade_date=day.isoformat())
                if not rows:
                    logger.info("dce_no_quotes date=%s checkpoint_unchanged=true", day)
                    continue
                observed = True
                remaining = max_items - len(records)
                records.extend(rows[:remaining])
                if len(rows) > remaining:
                    # Never skip an unreturned contract in the same daily batch.
                    break
                checkpoint = day
                if bootstrap or len(records) == max_items:
                    break
            if not observed and any(day.weekday() < 5 for day in days):
                raise DceSourceError("No corn quotes in requested window; cursor unchanged (not yet published, unavailable contract, or schema change)")
            if incremental and checkpoint:
                self.advance_cursor(checkpoint.isoformat())
            logger.info("dce_complete records=%d checkpoint=%s bootstrap=%s", len(records), checkpoint, bootstrap)
            return records
        finally:
            if lock:
                lock.release()


# Keep a conventional uppercase spelling available to external callers.
DCEProductionCollector = DceProductionCollector
