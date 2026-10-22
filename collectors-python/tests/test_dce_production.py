"""Synthetic DCE schema fixtures for offline tests, never live-market evidence."""
import copy
import io
import json
import os
from pathlib import Path
import sys
import unittest
from datetime import date, datetime
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collectors.dce_production import DceProductionCollector, DceSourceError
from cursor import deferred_cursors
from test_boyar_production import FakeRedis

DAY = date(2026, 10, 21)
ROW = {"variety": "玉米", "contractId": "c2701", "open": "2,100", "high": "2150",
       "low": "2080", "close": "2130", "clearPrice": "2120", "lastClear": "2110",
       "volumn": "12,345", "openInterest": "45678"}


def payload(*rows):
    return {"code": 200, "data": list(rows) if rows else [copy.deepcopy(ROW)]}


class DceTests(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.sleep = Mock()
        self.opener = Mock()
        self.c = self.make()

    def make(self, **kwargs):
        return DceProductionCollector(redis_client=self.redis, opener=self.opener, sleep=self.sleep,
            uniform=lambda a, b: 2, now=lambda: datetime.fromisoformat("2026-10-22T12:00:00+08:00"),
            **kwargs)

    def test_field_mapping_and_real_source_metadata(self):
        result = self.c._parse_day(payload(), DAY)
        self.assertEqual(len(result), 1)
        r = result[0]
        self.assertEqual((r.business_date, r.value, r.unit), ("2026-10-21", 2130, "元/吨"))
        self.assertEqual(r.metadata["record_key"], "C2701")
        self.assertEqual(r.metadata["volume"], 12345)
        self.assertEqual(r.metadata["open_interest"], 45678)
        self.assertEqual(r.metadata["quality_grade"], "A")
        self.assertEqual(r.metadata["price_field"], "close")
        self.assertIs(r.metadata["is_mock"], False)
        self.assertEqual(r.indicator, "玉米期货价格")
        self.assertEqual(json.loads(r.original_text), ROW)

    def test_multiple_contracts_sorted_non_corn_and_summaries_excluded(self):
        other = {**ROW, "contractId": "c2705"}
        rows = self.c._parse_day(payload(other, ROW, {"variety": "玉米小计"},
            {"variety": "玉米淀粉", "contractId": "cs2701"},
            {"variety": "豆粕", "contractId": "m2701"}), DAY)
        self.assertEqual([r.metadata["contract"] for r in rows], ["C2701", "C2705"])

    def test_close_missing_uses_explicitly_labeled_settlement(self):
        for missing in (None, "--", "0"):
            r = self.c._parse_day(payload({**ROW, "close": missing}), DAY)[0]
            self.assertEqual(r.value, 2120)
            self.assertEqual(r.metadata["price_field"], "clearPrice")

    def test_invalid_numbers_rejected_not_zero_fallback(self):
        for bad in ("NaN", "-1", "2,13", "inf", True, "2130元/吨", "2100-2200", "1e309"):
            with self.subTest(bad=bad), self.assertRaises(DceSourceError):
                self.c._parse_day(payload({**ROW, "close": bad}), DAY)

    def test_missing_positive_price_and_invalid_volume_rejected(self):
        for changes in ({"close": "--", "clearPrice": "--"}, {"close": "0", "clearPrice": 0},
                        {"volumn": "1.2"}, {"low": 2200}, {"openInterest": -1}):
            with self.subTest(changes=changes), self.assertRaises(DceSourceError):
                self.c._parse_day(payload({**ROW, **changes}), DAY)

    def test_invalid_envelopes_and_schema_rejected(self):
        for p in ([], {}, {"data": None}, {"data": [], "success": False},
                  {"data": [], "code": 500}, {"data": [None]},
                  payload({**ROW, "contractId": "c2713"}),
                  payload({**ROW, "variety": "豆粕"}), payload(ROW, ROW)):
            with self.subTest(payload=p), self.assertRaises(DceSourceError):
                self.c._parse_day(p, DAY)

    def test_response_date_must_match_request_date(self):
        for p in ({**payload(), "tradeDate": "20261020"},
                  payload({**ROW, "tradeDate": "2026-10-20"})):
            with self.assertRaisesRegex(DceSourceError, "date differs"):
                self.c._parse_day(p, DAY)
        self.assertEqual(len(self.c._parse_day({**payload(), "tradeDate": "20261021"}, DAY)), 1)

    def test_contract_filter_has_separate_cursor_namespace(self):
        filtered = self.make(contracts=["c2701", "C2701"])
        self.assertNotEqual(filtered.cursor.key, self.c.cursor.key)
        self.assertEqual(filtered.cursor.key, self.make(contracts="C2701").cursor.key)
        rows = filtered._parse_day(payload(ROW, {**ROW, "contractId": "c2705"}), DAY)
        self.assertEqual(len(rows), 1)
        self.assertEqual(self.make(contracts="C2501,C2505").contracts, ("C2501", "C2505"))
        for invalid in ("cs2701", "C2713", "C0", "C2501;DROP"):
            with self.assertRaises(ValueError): self.make(contracts=invalid)

    def test_request_is_post_with_bound_trade_date_headers_and_pacing(self):
        self.opener.return_value = io.BytesIO(json.dumps(payload()).encode())
        self.assertEqual(self.c._fetch_day(DAY), payload())
        req = self.opener.call_args.args[0]
        self.assertEqual(req.method, "POST")
        self.assertEqual(json.loads(req.data)["tradeDate"], "20261021")
        self.assertEqual(req.get_header("Referer"), self.c.site_url)
        self.assertEqual(self.sleep.call_args.args, (2,))
        self.assertEqual(self.opener.call_args.kwargs["timeout"], 30)

    def test_network_retries_three_times_with_backoff_and_ua_rotation(self):
        self.opener.side_effect = [URLError("offline")] * 3 + [io.BytesIO(b'{"data": []}')]
        self.c._fetch_day(DAY)
        self.assertEqual(self.opener.call_count, 4)
        self.assertEqual([c.args[0] for c in self.sleep.call_args_list], [2, 1, 2, 2, 2, 4, 2])
        reqs = [c.args[0] for c in self.opener.call_args_list]
        self.assertNotEqual(reqs[0].get_header("User-agent"), reqs[1].get_header("User-agent"))

    def test_permanent_http_error_is_not_retried(self):
        self.opener.side_effect = HTTPError(self.c.api_url, 412, "challenge", {}, None)
        with self.assertRaises(HTTPError): self.c.collect()
        self.assertEqual(self.opener.call_count, 1)
        self.assertIsNone(self.c.get_cursor())
        self.assertFalse(self.redis.locked)

    def test_transient_http_errors_retry_but_budget_is_finite(self):
        for code in (408, 429, 503):
            self.opener.reset_mock()
            self.opener.side_effect = HTTPError(self.c.api_url, code, "busy", {}, None)
            with self.assertRaises(HTTPError): self.c._fetch_day(DAY)
            self.assertEqual(self.opener.call_count, 4)

    def test_html_challenge_fails_without_synthetic_fallback(self):
        self.opener.return_value = io.BytesIO(b"<html>Access denied</html>")
        with self.assertRaisesRegex(DceSourceError, "non-JSON"): self.c.collect()
        self.assertIsNone(self.c.get_cursor())

    def test_bootstrap_then_second_run_has_no_requests(self):
        self.c._fetch_day = Mock(return_value=payload())
        self.assertEqual(len(self.c.collect()), 1)
        self.assertEqual(self.c.get_cursor(), "2026-10-21")
        self.assertEqual(self.c.collect(), [])
        self.c._fetch_day.assert_called_once_with(DAY)

    def test_holiday_bootstrap_uses_last_actual_trading_date(self):
        self.c._fetch_day = Mock(side_effect=[{"data": []}, payload()])
        self.assertEqual(self.c.collect()[0].business_date, "2026-10-20")
        self.assertEqual(self.c.get_cursor(), "2026-10-20")

    def test_incremental_forward_collects_missing_days_and_skips_weekends(self):
        self.redis.set(self.c.cursor.key, "2026-10-16")
        self.c._fetch_day = Mock(return_value=payload())
        rows = self.c.collect()
        self.assertEqual([r.business_date for r in rows], ["2026-10-19", "2026-10-20", "2026-10-21"])
        self.assertEqual(self.c.get_cursor(), "2026-10-21")
        self.assertEqual(self.c._fetch_day.call_count, 3)

    def test_forward_window_is_bounded(self):
        c = self.make(start_date="2026-10-19", max_days=2)
        c._fetch_day = Mock(return_value=payload())
        self.assertEqual(len(c.collect()), 2)
        self.assertEqual(c.get_cursor(), "2026-10-20")

    def test_truncated_same_day_does_not_checkpoint(self):
        self.c._fetch_day = Mock(return_value=payload(ROW, {**ROW, "contractId": "c2705"}))
        self.assertEqual(len(self.c.collect(max_items=1)), 1)
        self.assertIsNone(self.c.get_cursor())
        self.assertEqual(len(self.c.collect()), 2)
        self.assertEqual(self.c.get_cursor(), "2026-10-21")

    def test_partial_later_day_only_acknowledges_completed_day(self):
        self.redis.set(self.c.cursor.key, "2026-10-19")
        self.c._fetch_day = Mock(return_value=payload(ROW, {**ROW, "contractId": "c2705"}))
        self.assertEqual(len(self.c.collect(max_items=3)), 3)
        self.assertEqual(self.c.get_cursor(), "2026-10-20")

    def test_later_request_failure_does_not_commit_any_checkpoint(self):
        c = self.make(start_date="2026-10-20")
        c._fetch_day = Mock(side_effect=[payload(), TimeoutError("offline")])
        with self.assertRaises(TimeoutError): c.collect()
        self.assertIsNone(c.get_cursor())

    def test_empty_window_fails_closed(self):
        self.c._fetch_day = Mock(return_value={"data": []})
        with self.assertRaisesRegex(DceSourceError, "No corn quotes"): self.c.collect()
        self.assertIsNone(self.c.get_cursor())
        self.assertLessEqual(self.c._fetch_day.call_count, 14)

    def test_deferred_checkpoints_are_not_committed_by_runner(self):
        self.c._fetch_day = Mock(return_value=payload())
        with deferred_cursors() as updates:
            self.c.collect()
        self.assertIsNone(self.c.get_cursor())
        self.assertEqual(updates[self.c.cursor.key]["value"], "2026-10-21")
        self.assertEqual(updates[self.c.cursor.key]["namespace"], "dce")

    def test_nonincremental_does_not_touch_redis(self):
        self.c.cursor.get = Mock(side_effect=RuntimeError("must not read"))
        self.c._fetch_day = Mock(return_value=payload())
        self.assertEqual(len(self.c.collect(incremental=False)), 1)
        self.assertEqual(self.redis.data, {})

    def test_lock_prevents_overlap(self):
        self.redis.locked = True
        with self.assertRaisesRegex(RuntimeError, "Another DCE"): self.c.collect()

    def test_invalid_limits_dates_and_clock(self):
        for limit in (0, -1, True, 1.5):
            with self.assertRaises(ValueError): self.c.collect(max_items=limit)
        for kwargs in ({"end_date": "2026-10-22"}, {"start_date": "2026-10-22"},
                       {"end_date": "yesterday"}, {"end_date": "2026-02-30"}):
            with self.assertRaises(ValueError): self.c.collect(**kwargs)
        for value in (0, 367, True):
            with self.assertRaises(ValueError): self.make(max_days=value)
        self.c._now = lambda: datetime(2026, 10, 22)
        with self.assertRaises(ValueError): self.c.collect()

    def test_after_cutoff_uses_beijing_date_not_utc(self):
        self.c._now = lambda: datetime.fromisoformat("2026-10-22T10:00:00+00:00")
        self.assertEqual(self.c._latest_completed_day(), date(2026, 10, 22))


class DceRealRedisTests(unittest.TestCase):
    @unittest.skipUnless(os.getenv("BOYAR_TEST_REDIS_URL"), "set isolated Redis URL to enable")
    def test_real_redis_monotonic_deferred_commit_and_second_run(self):
        import redis
        import uuid
        client = redis.Redis.from_url(os.environ["BOYAR_TEST_REDIS_URL"], decode_responses=True)
        key = "test:dce:" + uuid.uuid4().hex
        c = DceProductionCollector(redis_client=client, cursor_key=key,
            now=lambda: datetime.fromisoformat("2026-10-22T12:00:00+08:00"))
        c._fetch_day = Mock(return_value=payload())
        try:
            with deferred_cursors() as pending:
                self.assertEqual(len(c.collect()), 1)
            self.assertIsNone(client.get(key))
            c.cursor.advance(pending[key]["value"])
            self.assertEqual(client.get(key), "2026-10-21")
            self.assertEqual(c.collect(), [])
            c.cursor.advance("2026-10-20")
            self.assertEqual(client.get(key), "2026-10-21")
        finally:
            client.delete(key, key + ":lock")


if __name__ == "__main__":
    unittest.main()
