from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cursor import deferred_cursors
from collectors.sina_production import SinaProductionCollector
from test_boyar_production import FakeRedis
from test_sina_production import PAGE, ARTICLE, QUOTE


class SinaCursorTests(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.c = SinaProductionCollector(redis_client=self.redis, sleep=lambda _: None,
                                         cursor_key='collector:sina:last_date')

    def run_sources(self, pages):
        self.c._request = Mock(side_effect=pages)
        return self.c.collect()

    def test_two_runs_only_new_data_second_skips_article_fetch(self):
        self.assertEqual(len(self.run_sources([PAGE, ARTICLE, QUOTE])), 3)
        self.assertEqual(self.redis.get('collector:sina:last_date'), '2026-10-22')
        self.assertEqual(self.redis.get('collector:sina:last_date:futures'), '2026-10-22')
        self.assertEqual(self.run_sources([PAGE, QUOTE]), [])
        self.assertEqual(self.c._request.call_count, 2)

    def test_new_observation_day_advances(self):
        self.run_sources([PAGE, ARTICLE, QUOTE])
        tomorrow = [x.replace('2026-10-22', '2026-10-23').replace('2026年10月22日', '2026年10月23日')
                    for x in (PAGE, ARTICLE, QUOTE)]
        self.assertEqual(len(self.run_sources(tomorrow)), 3)
        self.assertEqual(self.c.get_cursor(), '2026-10-23')

    def test_futures_today_does_not_skip_yesterdays_spot_update(self):
        old_page, old_article = [x.replace('2026-10-22', '2026-10-21').replace('2026年10月22日', '2026年10月21日')
                                 for x in (PAGE, ARTICLE)]
        self.assertEqual(len(self.run_sources([old_page, old_article, QUOTE])), 3)
        self.assertEqual(len(self.run_sources([PAGE, ARTICLE, QUOTE])), 2)
        self.assertEqual(self.c.get_cursor(), '2026-10-22')

    def test_partial_batch_does_not_checkpoint_unreturned_spot(self):
        self.c._request = Mock(side_effect=[PAGE, ARTICLE, QUOTE])
        self.assertEqual(len(self.c.collect(max_items=1)), 1)
        self.assertIsNone(self.c.get_cursor())
        self.assertEqual(self.c.futures_cursor.get(), '2026-10-22')
        self.assertEqual(len(self.run_sources([PAGE, ARTICLE, QUOTE])), 2)
        self.assertEqual(self.c.get_cursor(), '2026-10-22')

    def test_source_failure_does_not_advance_either_stream(self):
        self.c._request = Mock(side_effect=[PAGE, ARTICLE, TimeoutError('offline')])
        with self.assertRaises(TimeoutError): self.c.collect()
        self.assertIsNone(self.c.get_cursor())
        self.assertIsNone(self.c.futures_cursor.get())
        self.assertFalse(self.redis.locked)

    def test_deferred_acknowledgement_leaves_redis_unchanged(self):
        self.c._request = Mock(side_effect=[PAGE, ARTICLE, QUOTE])
        with deferred_cursors() as updates:
            self.assertEqual(len(self.c.collect()), 3)
        self.assertEqual(len(updates), 2)
        self.assertIsNone(self.c.get_cursor())
        self.assertIsNone(self.c.futures_cursor.get())

    def test_nonincremental_diagnostic_never_reads_or_writes_cursor(self):
        self.c._request = Mock(side_effect=[PAGE, ARTICLE, QUOTE])
        self.c.cursor.get = Mock(side_effect=RuntimeError('must not read'))
        self.assertEqual(len(self.c.collect(incremental=False)), 3)
        self.assertEqual(self.redis.data, {})

    def test_lock_prevents_concurrent_incremental_runs(self):
        self.redis.locked = True
        with self.assertRaisesRegex(RuntimeError, 'Another Sina'): self.c.collect()
