"""Live P1 release checks against the rebuilt backend; requests real Sina data."""
import json
from pathlib import Path
import time
import unittest
from urllib.parse import urlencode
from api_regression import request


class ReleaseRegressionTests(unittest.TestCase):
    def test_date_range_input_cannot_panic(self):
        for days in (-2147483648, -1, 0, 36501, 2147483647):
            for path, params in (
                ('/api/data/latest', {'days': days}),
                ('/api/data/trend', {'days': days, 'indicator': '玉米现货价格'}),
            ):
                with self.subTest(path=path, days=days):
                    status, body = request(path + '?' + urlencode(params))
                    self.assertEqual(status, 400, body)
                    self.assertFalse(body['success'], body)
        self.assertEqual(request('/health')[0], 200)

    def test_stats_without_unwrap(self):
        status, payload = request('/api/data/stats')
        self.assertEqual(status, 200, payload)
        self.assertTrue(payload['success'])
        self.assertGreater(payload['data']['total_records'], 0)
        self.assertIsNotNone(payload['data']['latest_collection'])

    def test_repeat_real_sina_runs(self):
        evidence = []
        for _ in range(3):
            status, payload = request('/api/collectors/run', {'collector_name': 'sina_production'})
            self.assertEqual(status, 200, payload)
            self.assertTrue(payload['success'], payload)
            self.assertEqual(payload['data']['records_collected'], 41, payload)
            run_id = payload['data']['run_id']
            status, history = request('/api/adapters/adapter_sina_spot/runs?limit=100')
            self.assertEqual(status, 200)
            row = next(r for r in history['data'] if r['id'] == run_id)
            self.assertEqual(row['status'], 'success', row)
            self.assertEqual(row['failed_records'], 0, row)
            self.assertIsNone(row['error_message'], row)
            self.assertEqual(row['new_records'] + row['duplicate_records'], 41, row)
            evidence.append({'response': payload, 'history': row})
        status, payload = request('/api/adapters/adapter_sina_spot/records?limit=100')
        self.assertEqual(status, 200)
        rows = [r for r in payload['data'] if r.get('metadata') and r['metadata'].get('is_mock') is False]
        self.assertTrue(rows)
        self.assertTrue(all(r['source_url'].startswith(('https://finance.sina.com.cn/',
                                                       'https://hq.sinajs.cn/')) for r in rows))
        path = Path(__file__).resolve().parents[2] / 'docs/reports/p1-release-evidence.json'
        path.write_text(json.dumps({'runs': evidence, 'verified_non_mock_records': len(rows)},
                                   ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main(verbosity=2)
