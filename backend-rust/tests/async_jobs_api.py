"""Live async API regression. Run Boyar with BOYAR_SCAN_LIMIT=2 for bounded smoke tests.
Test-only rows are cleaned using their generated UUIDs; production Boyar evidence remains.
"""
import json
from pathlib import Path
import subprocess
import time
import unittest
from uuid import UUID, uuid4
from history_api import request


def delete_job(job):
    job = str(UUID(job))
    subprocess.run(['docker', 'exec', 'corn_postgres', 'psql', '-X', '-v', 'ON_ERROR_STOP=1',
                    '-U', 'corn_user', '-d', 'corn_research', '-c',
                    f"DELETE FROM async_jobs WHERE id='{job}'::uuid AND status IN ('succeeded','failed');"],
                   check=True, stdout=subprocess.DEVNULL)


class AsyncJobsTests(unittest.TestCase):
    def api(self, path, method='GET', body=None, status=200):
        code, result = request(path, method, body)
        self.assertEqual(code, status, result)
        self.assertTrue(result['success'], result)
        return result['data']

    def submit(self, collector):
        start = time.monotonic()
        job = self.api('/api/collectors/run/async', 'POST', {'collector_name': collector}, status=202)
        self.assertLess(time.monotonic() - start, 2, job)
        self.assertEqual(job['status'], 'queued')
        return job['job_id']

    def poll(self, job):
        events = []
        for _ in range(900):
            row = self.api('/api/jobs/' + job)
            if not events or events[-1] != (row['status'], row['progress'], row['phase']):
                events.append((row['status'], row['progress'], row['phase']))
            self.assertTrue(0 <= row['progress'] <= 100)
            self.assertEqual([x[1] for x in events], sorted(x[1] for x in events))
            if row['status'] in ('succeeded', 'failed'):
                return row, events
            time.sleep(0.2)
        self.fail('Async job failed to finish in 180 seconds: ' + job)

    def test_mock_persists_results_and_history(self):
        job = self.submit('mock')
        self.addCleanup(delete_job, job)
        row, events = self.poll(job)
        self.assertEqual(row['status'], 'succeeded', row)
        self.assertEqual(row['progress'], 100)
        self.assertEqual(row['result']['records_collected'], 10)
        self.assertIsNone(row['error_message'])
        self.assertTrue(row['run_id'])
        self.assertIsNotNone(row['completed_at'])

    def test_validation_and_unknown_job(self):
        for body in ({'collector_name': 'mock', 'max_items': 0},
                     {'collector_name': 'mock', 'max_items': 1001},
                     {'collector_name': ' '}, {'collector_name': '__not_registered__'}):
            self.assertEqual(request('/api/collectors/run/async', 'POST', body)[0], 400)
        self.assertEqual(request('/api/collectors/run/async', 'POST', {})[0], 422)
        self.assertEqual(request('/api/jobs/' + str(uuid4()))[0], 404)
        self.assertEqual(request('/api/jobs/not-a-uuid')[0], 400)

    def test_failed_python_finalizes_job_and_run(self):
        script = '__async_failure_' + uuid4().hex[:10]
        adapter = 'test_async_' + uuid4().hex[:10]
        self.api('/api/adapters', 'POST', {'id': adapter, 'name': script, 'source_id': 'boyar',
                                         'script_file': script, 'topic_name': 'test_async'})
        self.addCleanup(self.api, '/api/adapters/' + adapter, 'DELETE')
        job = self.submit(script)
        self.addCleanup(delete_job, job)
        row, _ = self.poll(job)
        self.assertEqual(row['status'], 'failed', row)
        self.assertIn('Unknown collector', row['error_message'])
        self.assertLess(row['progress'], 100)
        runs = self.api('/api/adapters/' + adapter + '/runs')
        self.assertEqual(next(r for r in runs if r['id'] == row['run_id'])['status'], 'failed')

    def test_real_boyar_background_progress_and_overlap(self):
        # This is an actual remote scan, not mock. A bounded runtime scan limit is required.
        job = self.submit('boyar_production')
        self.assertEqual(request('/api/collectors/run/async', 'POST',
                                 {'collector_name': 'boyar'})[0], 409)
        row, events = self.poll(job)
        self.assertEqual(row['status'], 'succeeded', row)
        self.assertEqual(row['progress'], 100)
        self.assertTrue(any(0 < event[1] < 100 for event in events), events)
        path = Path(__file__).resolve().parents[2] / 'docs/reports/phase2-task1-live.json'
        path.write_text(json.dumps({'job': row, 'progress_observed': events},
                                   ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main(verbosity=2)
