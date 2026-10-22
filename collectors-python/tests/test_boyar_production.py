import io
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import BoyarConfig, configure_boyar_logging
from collectors.boyar_production import BoyarProductionCollector


KEY = "collector:boyar:last_article_id"


class FakeLock:
    def __init__(self, redis):
        self.redis = redis

    def acquire(self, blocking=False):
        if self.redis.locked:
            return False
        self.redis.locked = True
        return True

    def release(self):
        self.redis.locked = False


class FakeRedis:
    def __init__(self):
        self.data = {}
        self.locked = False

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = str(value)

    def eval(self, script, numkeys, key, exists, expected, value):
        current = self.get(key)
        if (exists == '0' and current is not None) or (exists == '1' and current != expected):
            return 0
        self.set(key, value)
        return 1

    def lock(self, key, timeout):
        return FakeLock(self)


class Clock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def page(day=8, year=2026):
    return (f"<title>{year}年10月{day}日山东玉米到货</title>"
            "山东深加工企业晨间到车辆1027台").encode()


class BoyarTests(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.clock = Clock()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = BoyarConfig(start_article_id=100, scan_limit=5)
        self.collector = self.make_collector()

    def make_collector(self):
        collector = BoyarProductionCollector(
            redis_client=self.redis, data_dir=self.temp.name, config=self.config,
            sleep=self.clock.sleep, clock=self.clock.monotonic, rng=random.Random(7), log_dir=str(Path(self.temp.name) / "logs"),
        )
        self.addCleanup(self.close_logger, collector.logger)
        return collector

    @staticmethod
    def close_logger(logger):
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

    def response(self, html=None):
        return io.BytesIO(page() if html is None else html)

    def http_error(self, code, message):
        error = HTTPError("url", code, message, {}, io.BytesIO())
        self.addCleanup(error.close)
        return error

    @patch("urllib.request.urlopen")
    def test_two_runs_fetch_only_new_ids(self, opener):
        opener.side_effect = lambda *a, **kw: self.response()
        first = self.collector.collect(end_id=101)
        self.assertEqual([r.metadata["article_id"] for r in first], [100, 101])
        self.assertEqual(self.redis.get(KEY), "101")
        second = self.make_collector().collect(end_id=102)
        self.assertEqual([r.metadata["article_id"] for r in second], [102])
        self.assertEqual(self.redis.get(KEY), "102")
        self.assertEqual([call.args[0].full_url.rsplit("/", 1)[1] for call in opener.call_args_list],
                         ["100.html", "101.html", "102.html"])

    @patch("urllib.request.urlopen")
    def test_duplicate_stops_without_network(self, opener):
        self.redis.set(KEY, 100)
        self.assertEqual(self.collector.collect(start_id=100, end_id=102), [])
        opener.assert_not_called()
        self.assertEqual(self.redis.get(KEY), "100")

    @patch("urllib.request.urlopen")
    def test_random_spacing_and_header_rotation(self, opener):
        starts, headers = [], []
        def fetch(req, **kwargs):
            starts.append(self.clock.now)
            headers.append(dict(req.header_items()))
            return self.response()
        opener.side_effect = fetch
        self.collector.collect(end_id=104)
        gaps = [b - a for a, b in zip(starts, starts[1:])]
        self.assertTrue(all(1 <= gap <= 3 for gap in gaps), gaps)
        self.assertGreater(len(set(gaps)), 1)
        for a, b in zip(headers, headers[1:]):
            self.assertNotEqual(a["User-agent"], b["User-agent"])
        self.assertTrue(all(h["Referer"] == "https://m.boyar.cn/" for h in headers))

    @patch("urllib.request.urlopen")
    def test_retry_then_success_is_rate_limited(self, opener):
        opener.side_effect = [URLError("temporary"), TimeoutError("timeout"), self.response()]
        with self.assertLogs("collectors.boyar_production", level="WARNING") as logs:
            records = self.collector.collect(end_id=100)
        self.assertEqual(len(records), 1)
        self.assertEqual(opener.call_count, 3)
        retry_logs = [message for message in logs.output if "retry in " in message]
        self.assertEqual(len(retry_logs), 2)
        self.assertIn("retry in 1.0s", retry_logs[0])
        self.assertIn("retry in 2.0s", retry_logs[1])
        self.assertGreaterEqual(len(self.clock.sleeps), 3)
        self.assertEqual(self.redis.get(KEY), "100")

    @patch("urllib.request.urlopen")
    def test_exhaustion_does_not_advance_batch_checkpoint(self, opener):
        self.redis.set(KEY, 99)
        opener.side_effect = [self.response()] + [URLError("offline")] * 4
        with self.assertLogs("collectors.boyar_production", level="WARNING") as logs:
            with self.assertRaises(URLError):
                self.collector.collect(end_id=101)
        self.assertEqual(opener.call_count, 5)
        for seconds in (1, 2, 4):
            self.assertTrue(any(f"retry in {seconds}.0s" in line for line in logs.output))
        self.assertTrue(any("checkpoint is unchanged" in line for line in logs.output))
        self.assertEqual(self.redis.get(KEY), "99")
        self.assertFalse(self.redis.locked)

    @patch("urllib.request.urlopen")
    def test_404_frontier_stops_and_is_retried_next_run(self, opener):
        opener.side_effect = [self.response(), self.http_error(404, "missing")]
        self.assertEqual(len(self.collector.collect(end_id=104)), 1)
        self.assertEqual(self.redis.get(KEY), "100")
        opener.side_effect = lambda *a, **kw: self.response()
        self.make_collector().collect(end_id=101)
        self.assertTrue(opener.call_args.args[0].full_url.endswith("/101.html"))

    @patch("urllib.request.urlopen")
    def test_permanent_403_not_retried(self, opener):
        opener.side_effect = self.http_error(403, "forbidden")
        with self.assertLogs("collectors.boyar_production", level="ERROR"):
            with self.assertRaises(HTTPError):
                self.collector.collect(end_id=100)
        self.assertEqual(opener.call_count, 1)
        self.assertIsNone(self.redis.get(KEY))

    @patch("urllib.request.urlopen")
    def test_429_and_503_are_retried(self, opener):
        opener.side_effect = [self.http_error(429, "slow down"),
                              self.http_error(503, "unavailable"), self.response()]
        with self.assertLogs("collectors.boyar_production", level="WARNING"):
            self.assertEqual(len(self.collector.collect(end_id=100)), 1)
        self.assertEqual(opener.call_count, 3)

    @patch("urllib.request.urlopen")
    def test_archive_is_complete_and_path_is_returned(self, opener):
        opener.side_effect = lambda *a, **kw: self.response()
        record = self.collector.collect(end_id=100)[0]
        with open(record.metadata["html_path"], "rb") as archive:
            self.assertEqual(archive.read(), page())
        self.assertEqual(list(Path(self.temp.name).rglob("*.tmp")), [])
        path = Path(record.metadata["html_path"])
        self.assertEqual(path.name, "article_100.html")
        self.assertEqual(path.parent.parent, Path(self.temp.name) / "html" / "boyar")

    @patch("urllib.request.urlopen")
    def test_non_target_html_is_archived_too(self, opener):
        html = b"<title>Unrelated article</title>"
        opener.side_effect = lambda *a, **kw: self.response(html)
        self.assertEqual(self.collector.collect(end_id=100), [])
        paths = list((Path(self.temp.name) / "html" / "boyar").rglob("article_100.html"))
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].read_bytes(), html)

    def test_archive_rejects_invalid_article_ids(self):
        for article_id in ["../escape", 0, -1, True]:
            with self.assertRaises(ValueError):
                self.collector.save_html(article_id, "content")

    @patch("urllib.request.urlopen")
    def test_atomic_write_failure_leaves_no_partial_archive(self, opener):
        opener.side_effect = lambda *a, **kw: self.response()
        with patch("os.replace", side_effect=OSError("write failed")):
            with self.assertLogs("collectors.boyar_production", level="ERROR"):
                with self.assertRaises(OSError):
                    self.collector.collect(end_id=100)
        self.assertEqual(list(Path(self.temp.name).rglob("*.tmp")), [])
        self.assertEqual(list(Path(self.temp.name).rglob("article_100.html")), [])
        self.assertIsNone(self.redis.get(KEY))

    @patch("urllib.request.urlopen")
    def test_log_contains_run_stats_and_archive_path(self, opener):
        opener.side_effect = lambda *a, **kw: self.response()
        self.collector.collect(end_id=101)
        log = (Path(self.temp.name) / "logs" / "boyar.log").read_text()
        self.assertIn("run_started", log)
        self.assertIn("html_saved article_id=100", log)
        summary = json.loads(log.split("run_finished ")[-1].strip())
        self.assertEqual(summary["status"], "success")
        self.assertEqual(summary["records"], 2)
        self.assertEqual(summary["scanned"], 2)
        self.assertEqual(summary["requests"], 2)
        self.assertEqual(summary["archives"], 2)
        self.assertEqual(summary["retries"], 0)
        self.assertGreaterEqual(summary["elapsed_seconds"], 1)

    def test_logging_configuration_is_idempotent(self):
        same = configure_boyar_logging(self.config, str(Path(self.temp.name) / "logs"))
        self.assertIs(same, self.collector.logger)
        handlers = [h for h in same.handlers if isinstance(h, RotatingFileHandler)]
        self.assertEqual(len(handlers), 1)
        self.assertEqual(handlers[0].maxBytes, 10 * 1024 * 1024)
        self.assertEqual(handlers[0].backupCount, 5)

    def test_log_rotation_is_bounded(self):
        from dataclasses import replace
        directory = Path(self.temp.name) / "rotation"
        log = configure_boyar_logging(replace(self.config, log_max_bytes=200, log_backup_count=2), directory)
        self.addCleanup(self.close_logger, log)
        for i in range(30):
            log.info("rotation-record-%02d %s", i, "x" * 80)
        self.assertTrue((directory / "boyar.log.1").exists())
        self.assertTrue((directory / "boyar.log.2").exists())
        self.assertFalse((directory / "boyar.log.3").exists())
        self.assertIn("rotation-record-29", (directory / "boyar.log").read_text())

    def test_two_processes_share_log_without_lost_lines(self):
        directory = Path(self.temp.name) / "process-logs"
        script = """
import sys
from config import BoyarConfig, configure_boyar_logging
log = configure_boyar_logging(BoyarConfig(), sys.argv[1])
for i in range(30):
    log.info('worker=%s record=%s', sys.argv[2], i)
"""
        processes = [subprocess.Popen([sys.executable, "-c", script, str(directory), str(i)],
                       cwd=Path(__file__).resolve().parents[1]) for i in range(2)]
        for process in processes:
            self.assertEqual(process.wait(timeout=20), 0)
        content = (directory / "boyar.log").read_text()
        self.assertEqual(len(content.splitlines()), 60)
        for worker in range(2):
            for record in range(30):
                self.assertIn(f"worker={worker} record={record}\n", content)

    @patch("urllib.request.urlopen")
    def test_disk_failure_keeps_checkpoint(self, opener):
        opener.side_effect = lambda *a, **kw: self.response()
        with patch.object(self.collector, "_save_raw_html", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.collector.collect(end_id=100)
        self.assertIsNone(self.redis.get(KEY))

    @patch("urllib.request.urlopen")
    def test_max_items_and_scan_limit(self, opener):
        opener.side_effect = lambda *a, **kw: self.response()
        self.assertEqual(len(self.collector.collect(max_items=1)), 1)
        self.assertEqual(opener.call_count, 1)
        self.assertEqual(len(self.collector.collect(end_id=999, max_items=100)), 5)

    @patch("urllib.request.urlopen")
    def test_non_target_pages_advance_processed_cursor(self, opener):
        opener.side_effect = lambda *a, **kw: self.response(b"<title>Other market article</title>")
        self.assertEqual(self.collector.collect(end_id=101), [])
        self.assertEqual(self.redis.get(KEY), "101")

    @patch("urllib.request.urlopen")
    def test_full_scan_does_not_modify_redis(self, opener):
        self.redis.set(KEY, 200)
        opener.side_effect = lambda *a, **kw: self.response()
        self.assertEqual(len(self.collector.collect(start_id=100, end_id=100, incremental=False)), 1)
        self.assertEqual(self.redis.get(KEY), "200")

    @patch("urllib.request.urlopen")
    def test_redis_failure_does_not_fall_back_to_full_scan(self, opener):
        self.redis.get = Mock(side_effect=ConnectionError("redis down"))
        with self.assertRaises(ConnectionError):
            self.collector.collect()
        opener.assert_not_called()
        self.assertFalse(self.redis.locked)

    @patch("urllib.request.urlopen")
    def test_invalid_cursor_is_not_ignored(self, opener):
        self.redis.set(KEY, "bad value")
        with self.assertRaises(ValueError):
            self.collector.collect()
        opener.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_concurrent_run_rejected(self, opener):
        self.redis.locked = True
        with self.assertRaisesRegex(RuntimeError, "Another Boyar"):
            self.collector.collect()
        opener.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_year_is_not_hard_coded(self, opener):
        opener.side_effect = lambda *a, **kw: self.response(page(year=2027))
        self.assertEqual(self.collector.collect(end_id=100)[0].business_date, "2027-10-08")

    def test_config_validation_and_env(self):
        with patch.dict("os.environ", {"REDIS_URL": "redis://redis:6379/0", "BOYAR_START_ARTICLE_ID": "123"}):
            self.assertEqual(BoyarConfig().redis_url, "redis://redis:6379/0")
            self.assertEqual(BoyarConfig().start_article_id, 123)
        for kwargs in [{"scan_limit": 0}, {"min_interval": 0}, {"max_retries": 4}, {"user_agents": ()}]:
            with self.assertRaises(ValueError):
                BoyarConfig(**kwargs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
