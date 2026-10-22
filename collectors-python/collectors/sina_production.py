"""Real Sina corn prices; source errors must never become synthetic observations."""
import logging
import math
import os
import random
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import List
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential

from config import BoyarConfig
from .base import BaseCollector, RawDataRecord

logger = logging.getLogger(__name__)


class SinaSourceError(RuntimeError):
    pass


class SinaProductionCollector(BaseCollector):
    collector_id = "sina_corn_production"
    site_name = "新浪财经"
    site_url = "https://finance.sina.com.cn/money/future/C/"
    source_name = site_name
    source_url = site_url
    source_type = "public_media"

    def __init__(self, *, opener=None, sleep=None, uniform=None, symbols=None):
        self._opener = opener or urllib.request.urlopen
        self._sleep = sleep or time.sleep
        self._uniform = uniform or random.uniform
        self.symbols = tuple(symbols if symbols is not None else
                             os.getenv("SINA_FUTURES_SYMBOLS", "nf_C0").split(","))
        if not self.symbols or any(not re.fullmatch(r"nf_C(?:0|\d{4})", s) for s in self.symbols):
            raise ValueError("SINA_FUTURES_SYMBOLS must contain corn symbols, e.g. nf_C0,nf_C2701")
        self.request_timeout = 30
        self.max_retries = 3
        # Sina redirects mobile UAs to a CBOT SPA with no domestic corn news/table.
        self.user_agents = tuple(ua for ua in BoyarConfig.user_agents
                                 if not any(m in ua for m in ("Mobile", "iPhone", "Android")))
        if not self.user_agents:
            raise ValueError("Sina requires at least one desktop User-Agent")
        self._ua_index = random.randrange(len(self.user_agents))

    @staticmethod
    def _retryable(exc):
        if isinstance(exc, urllib.error.HTTPError):
            return exc.code in (408, 429) or 500 <= exc.code < 600
        return isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError))

    def _request(self, url):
        for attempt in Retrying(
            stop=stop_after_attempt(self.max_retries + 1),
            wait=wait_exponential(multiplier=1, min=1, max=4),
            retry=retry_if_exception(self._retryable), sleep=self._sleep, reraise=True,
        ):
            with attempt:
                self._sleep(self._uniform(1, 3))
                ua = self.user_agents[self._ua_index % len(self.user_agents)]
                self._ua_index += 1
                request = urllib.request.Request(url, headers={
                    "User-Agent": ua, "Referer": self.site_url,
                })
                try:
                    with self._opener(request, timeout=self.request_timeout) as response:
                        raw = response.read()
                        final_url = getattr(response, "geturl", lambda: url)()
                    logger.info("page_fetched url=%s final_url=%s bytes=%d attempt=%d",
                                url, final_url, len(raw), attempt.retry_state.attempt_number)
                    # Sina's channel and quote endpoint use GBK; articles use UTF-8.
                    try:
                        return raw.decode("utf-8-sig")
                    except UnicodeDecodeError:
                        return raw.decode("gb18030")
                except Exception as exc:
                    logger.warning("request_failed url=%s attempt=%s reason=%s", url,
                                   attempt.retry_state.attempt_number, exc)
                    raise

    def _fetch_page(self):
        return self._request(self.site_url)

    @staticmethod
    def _parse_date(text):
        match = re.fullmatch(r"\s*(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?\s*", text)
        if not match:
            raise ValueError("Missing or ambiguous business date: " + text)
        return datetime(*map(int, match.groups())).date().isoformat()

    @staticmethod
    def _parse_number(text):
        text = re.sub(r"\s+", "", text).replace("，", ",")
        match = re.fullmatch(r"([+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)(?:元/吨|元／吨)?", text)
        if not match:
            raise ValueError("Invalid price: " + text)
        value = float(match[1].replace(",", ""))
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Price must be finite and positive")
        return value

    def _record(self, date, value, region, url, text, metadata, published_at=None):
        future = metadata["topic_name"] == "corn_futures_price"
        return RawDataRecord(
            business_date=date, collected_at=datetime.now(timezone.utc),
            published_at=published_at, data_type="futures_price" if future else "spot_price",
            indicator="玉米期货价格" if future else "玉米现货价格", value=value,
            unit="元/吨", region=region, source_url=url, original_text=text,
            metadata={"collector_id": self.collector_id, "quality_grade": "B",
                      "is_mock": False, **metadata},
        )

    def _parse_spot(self, html, url):
        soup = BeautifulSoup(html, "lxml")
        title = soup.select_one("h1.main-title, h1")
        og_title = soup.select_one('meta[property="og:title"]')
        title_text = (title.get_text(" ", strip=True) if title else
                      og_title.get("content", "") if og_title else
                      soup.title.get_text(" ", strip=True) if soup.title else "")
        # Use the report's explicit observation date, never today's date or an unrelated page date.
        match = re.search(r"\d{4}[年/-]\d{1,2}[月/-]\d{1,2}日?", title_text)
        if "玉米" not in title_text or not match:
            logger.warning("spot_rejected url=%s reason=missing_report_date_or_corn_title title=%r",
                           url, title_text[:160])
            return []
        date = self._parse_date(match[0])
        publication = soup.select_one('meta[property="article:published_time"]')
        published = None
        if publication and publication.get("content"):
            try:
                published = datetime.fromisoformat(publication["content"])
            except ValueError:
                logger.warning("invalid_publication_timestamp url=%s value=%r", url, publication["content"])
        body = next((soup.select_one(selector) for selector in (
            "#artibody", "article", "#article", "#article_content", ".article-content", ".article"
        ) if soup.select_one(selector) is not None), None)
        if body is None:
            logger.warning("spot_rejected url=%s reason=missing_article_body title=%r", url, title_text[:160])
            return []
        records = {}
        for table in body.find_all("table"):
            rows = table.find_all("tr")
            # Only the unambiguous corn processor table, not the following soybean meal table.
            def normalized(text):
                return re.sub(r"\s+", "", text).replace("／", "/")

            header = next((i for i, r in enumerate(rows)
                           if any(label in normalized(r.get_text()) for label in
                                  ("深加工企业", "深加工厂家", "玉米加工企业"))
                           and "元/吨" in normalized(r.get_text())), None)
            if header is None:
                continue
            for row in rows[header + 1:]:
                cols = row.find_all(["td", "th"], recursive=False)
                if not cols:
                    continue
                if len(cols) != 2:
                    raise SinaSourceError("Corn spot table schema changed: expected two columns")
                enterprise, price = (c.get_text("", strip=True) for c in cols)
                if not enterprise:
                    raise SinaSourceError("Corn spot row has no enterprise")
                try:
                    value = self._parse_number(price)
                except ValueError as exc:
                    raise SinaSourceError(f"Invalid corn price for {enterprise}: {price}") from exc
                if enterprise in records:
                    raise SinaSourceError("Duplicate enterprise in report: " + enterprise)
                records[enterprise] = self._record(date, value, enterprise, url,
                    row.get_text(" | ", strip=True), {
                        "topic_name": "corn_spot_price", "enterprise": enterprise,
                        "record_key": enterprise, "title": title_text,
                        "price_basis": "report_quote; moisture/quality as stated in enterprise label",
                    }, published)
        logger.log(logging.INFO if records else logging.WARNING,
                   "spot_parsed url=%s title=%r tables=%d records=%d reason=%s",
                   url, title_text[:160], len(body.find_all("table")), len(records),
                   "ok" if records else "no_matching_corn_header")
        return list(records.values())

    def _discover_articles(self, html):
        page = BeautifulSoup(html, "lxml")
        candidates = []
        for a in page.find_all("a", href=True):
            title = a.get_text(strip=True) + " " + a.get("title", "")
            url = urljoin(self.site_url, a["href"])
            if url.startswith("http://"):
                url = "https://" + url[len("http://"):]
            parsed = urlparse(url)
            if (parsed.hostname == "finance.sina.com.cn" and "/money/future/" in parsed.path
                    and parsed.path.endswith(".shtml") and "玉米" in title
                    and re.search(r"/\d{4}-\d{2}-\d{2}/", parsed.path)
                    and any(word in title for word in ("市场信息", "行业资讯", "现货", "价格", "日报"))
                    and url not in candidates):
                candidates.append(url)
        candidates.sort(key=lambda url: (
            re.search(r"/\d{4}-\d{2}-\d{2}/", url)[0],
            any(word in url for word in ("/wemedia/", "/agri/")),
        ), reverse=True)
        logger.info("index_parsed title=%r bytes=%d candidates=%d",
                    page.title.get_text(strip=True) if page.title else "", len(html.encode("utf-8")),
                    len(candidates))
        return candidates

    def _parse_futures(self, text, url):
        records = []
        for symbol in self.symbols:
            match = re.search(r'var\s+hq_str_' + re.escape(symbol) + r'="([^"\r\n]*)";', text)
            fields = match[1].split(",") if match else []
            if len(fields) < 18 or fields[16] != "玉米":
                raise SinaSourceError("Missing/invalid Sina corn quote: " + symbol)
            date = self._parse_date(fields[17])
            if not re.fullmatch(r"\d{6}", fields[1]):
                raise SinaSourceError("Invalid quote time: " + fields[1])
            quote_at = datetime.fromisoformat(date + "T" + ":".join(
                fields[1][i:i+2] for i in (0, 2, 4)) + "+08:00")
            records.append(self._record(date, self._parse_number(fields[8]), "大连商品交易所",
                url, match[0], {
                    "topic_name": "corn_futures_price", "record_key": symbol,
                    "symbol": symbol, "contract_name": fields[0],
                    "continuous": symbol == "nf_C0", "quote_at": quote_at.isoformat(),
                    "price_field": "latest (index 8)", "open": fields[2],
                    "high": fields[3], "low": fields[4], "previous_settlement": fields[10],
                }))
        return records

    def collect(self, max_items: int = 100, **kwargs) -> List[RawDataRecord]:
        if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 1:
            raise ValueError("max_items must be a positive integer")
        candidates = self._discover_articles(self._fetch_page())
        if not candidates:
            logger.warning("no_candidates primary_url=%s trying_sina_futures_index", self.site_url)
            candidates = self._discover_articles(self._request("https://finance.sina.com.cn/futuremarket/"))
        spot = []
        failures = []
        for url in candidates[:5]:
            try:
                spot = self._parse_spot(self._request(url), url)
            except (SinaSourceError, ValueError, urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                logger.warning("candidate_failed url=%s reason=%s", url, exc, exc_info=True)
                failures.append(f"{url}: {type(exc).__name__}: {exc}")
                continue
            if spot:
                break
            failures.append(f"{url}: no dated corn processor table")
        if not spot:
            detail = "; ".join(failures) or "no eligible Sina article links (possible redirect or schema change)"
            raise SinaSourceError(f"No dated corn processor price table found; candidates={len(candidates)}; "
                                  f"attempted={min(len(candidates), 5)}; {detail}; no mock fallback")
        quote_url = "https://hq.sinajs.cn/list=" + ",".join(self.symbols)
        futures = self._parse_futures(self._request(quote_url), quote_url)
        # Reserve space for the futures quote; max_items always caps the full batch.
        records = (futures + spot)[:max_items]
        logger.info("collection_complete spot=%d futures=%d returned=%d", len(spot), len(futures), len(records))
        return records
