"""Real Redis integration, isolated keys and simulated HTTP (no site traffic)."""
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

import redis

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import BoyarConfig
from collectors.boyar_production import BoyarProductionCollector


@unittest.skipUnless(os.getenv("BOYAR_TEST_REDIS_URL"), "Set BOYAR_TEST_REDIS_URL for real Redis tests")
class BoyarRedisTests(unittest.TestCase):
    def setUp(self):
        self.client = redis.Redis.from_url(os.environ["BOYAR_TEST_REDIS_URL"], decode_responses=True)
        self.client.ping()
        self.key = "test:collector:boyar:" + uuid4().hex
        self.config = BoyarConfig(cursor_key=self.key, start_article_id=100, scan_limit=2)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.client.close)
        self.addCleanup(self.client.delete, self.key, self.key + ":lock")

    def collector(self):
        return BoyarProductionCollector(
            redis_client=self.client, config=self.config, data_dir=self.temp.name,
            sleep=lambda seconds: None, log_dir=str(Path(self.temp.name) / "logs"),
        )

    @patch("urllib.request.urlopen")
    def test_two_instances_resume_from_persisted_cursor(self, opener):
        opener.side_effect = lambda *a, **kw: io.BytesIO(
            "<title>2026年10月8日山东到车</title>山东深加工企业晨间到车辆1027台".encode())
        first = self.collector().collect(end_id=100)
        self.assertEqual(first[0].metadata["article_id"], 100)
        self.assertEqual(self.client.get(self.key), "100")
        second = self.collector().collect(end_id=101)
        self.assertEqual(second[0].metadata["article_id"], 101)
        self.assertEqual(self.client.get(self.key), "101")
        self.assertIsNone(self.client.get(self.key + ":lock"))
        self.assertEqual(self.collector().collect(start_id=100, end_id=102), [])
        self.assertEqual(opener.call_count, 2)

    def test_redis_lock_prevents_concurrent_scan(self):
        lock = self.client.lock(self.key + ":lock", timeout=30)
        self.assertTrue(lock.acquire(blocking=False))
        try:
            with self.assertRaisesRegex(RuntimeError, "Another Boyar"):
                self.collector().collect()
        finally:
            lock.release()

    @patch("urllib.request.urlopen", side_effect=TimeoutError("network unavailable"))
    def test_failed_batch_keeps_real_redis_checkpoint(self, opener):
        self.client.set(self.key, "99")
        with self.assertLogs("collectors.boyar_production", level="WARNING"):
            with self.assertRaises(TimeoutError):
                self.collector().collect(end_id=100)
        self.assertEqual(opener.call_count, 4)
        self.assertEqual(self.client.get(self.key), "99")
        self.assertIsNone(self.client.get(self.key + ":lock"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
