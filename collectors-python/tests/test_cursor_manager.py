import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4

import redis
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cursor import CursorManager, deferred_cursors
from test_boyar_production import FakeRedis


class CursorTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeRedis()

    def test_integer_key_compatibility_and_monotonicity(self):
        cursor = CursorManager('boyar', redis_client=self.client)
        self.assertEqual(cursor.key, 'collector:boyar:last_article_id')
        self.assertIsNone(cursor.get())
        self.assertEqual(cursor.advance(100), 100)
        self.assertEqual(cursor.advance(99), 100)
        self.assertEqual(cursor.get(), 100)
        self.assertEqual(cursor.advance('101'), 101)

    def test_date_validation_and_monotonicity(self):
        cursor = CursorManager('sina', 'date', redis_client=self.client)
        self.assertEqual(cursor.key, 'collector:sina:last_date')
        cursor.advance('2026-10-22')
        self.assertEqual(cursor.advance('2026-10-21'), '2026-10-22')
        for value in ('2026-02-30', '2026-1-01', 'today', None, 123):
            with self.assertRaises(ValueError): cursor.advance(value)
        self.assertEqual(cursor.get(), '2026-10-22')

    def test_corruption_fails_closed(self):
        cursor = CursorManager('boyar', redis_client=self.client)
        for value in ('abc', '0', '-1', '1.5', '01'):
            self.client.set(cursor.key, value)
            with self.assertRaises(ValueError): cursor.get()
            with self.assertRaises(ValueError): cursor.advance(10)
            self.assertEqual(self.client.get(cursor.key), value)

    def test_invalid_namespace_and_kind(self):
        for name, kind in (('bad:key','int'), ('','date'), ('boyar','float')):
            with self.assertRaises(ValueError): CursorManager(name, kind, redis_client=self.client)

    def test_staging_never_commits_without_ack(self):
        cursor = CursorManager('boyar', redis_client=self.client)
        with deferred_cursors() as updates:
            cursor.advance(100)
            cursor.advance(99)
            self.assertEqual(cursor.get(), 100)
            self.assertIsNone(self.client.get(cursor.key))
        self.assertEqual(updates[cursor.key]['value'], '100')
        self.assertIsNone(cursor.get())
        # Simulate persistence acknowledgement.
        cursor.advance(updates[cursor.key]['value'])
        self.assertEqual(cursor.get(), 100)

    def test_failed_session_keeps_checkpoint(self):
        cursor = CursorManager('boyar', redis_client=self.client)
        cursor.advance(10)
        with self.assertRaises(RuntimeError):
            with deferred_cursors():
                cursor.advance(11)
                raise RuntimeError('persistence failed')
        self.assertEqual(cursor.get(), 10)

    def test_redis_failure_is_not_missing_cursor(self):
        cursor = CursorManager('boyar', redis_client=self.client)
        with patch.object(self.client, 'get', side_effect=redis.ConnectionError('offline')):
            with self.assertRaises(redis.ConnectionError): cursor.get()
            with self.assertRaises(redis.ConnectionError): cursor.advance(10)


@unittest.skipUnless(os.getenv('BOYAR_TEST_REDIS_URL'), 'Set BOYAR_TEST_REDIS_URL for Redis tests')
class RealCursorTests(unittest.TestCase):
    def setUp(self):
        self.url = os.environ['BOYAR_TEST_REDIS_URL']
        self.client = redis.Redis.from_url(self.url, decode_responses=True)
        self.key = 'test:unified_cursor:' + uuid4().hex
        self.addCleanup(self.client.close)
        self.addCleanup(self.client.delete, self.key)

    def test_atomic_advance_concurrent_writers(self):
        cursor = CursorManager('test', redis_client=self.client, key=self.key)
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(cursor.advance, range(1, 65)))
        self.assertEqual(cursor.get(), 64)

    def test_backend_ack_script(self):
        cursor = CursorManager('test', 'date', redis_client=self.client, key=self.key)
        with deferred_cursors() as staged:
            cursor.advance('2026-10-22')
        self.assertIsNone(cursor.get())
        script = str(Path(__file__).resolve().parents[1] / 'commit_cursors.py')
        result = subprocess.run([sys.executable, script], input=json.dumps(list(staged.values())),
                                text=True, capture_output=True, env={**os.environ, 'REDIS_URL': self.url})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)['success'])
        self.assertEqual(cursor.get(), '2026-10-22')
