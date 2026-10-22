"""Real manual executions of the two seeded jobs; no automatic scheduling assertion.
For a bounded Boyar smoke test, deploy with BOYAR_SCAN_LIMIT=2 before running.
"""
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen

BASE = 'http://localhost:18000'
IDS = ['89000000-0000-4000-8000-000000000001', '89000000-0000-4000-8000-000000000002']


def api(path, method='GET'):
    with urlopen(Request(BASE + path, method=method), timeout=60) as response:
        data = json.load(response)
    assert data['success'], data
    return data['data']


def wait_run(job, execution):
    for _ in range(90):
        history = api(f'/api/scheduler/jobs/{job}/executions')
        run = next((x for x in history if x['id'] == execution), None)
        if run and run['status'] != 'running':
            assert run['status'] == 'success', run
            assert run['collection_run_id'], run
            return run
        time.sleep(1)
    raise AssertionError('Execution did not finish within 90 seconds: ' + execution)


jobs = {x['id']: x for x in api('/api/scheduler/jobs')}
for job in IDS:
    assert job in jobs, jobs
    assert jobs[job]['enabled'] is False, 'Examples must stay disabled pending Day 4 validation'
result = {'initial_jobs': [jobs[x] for x in IDS], 'executions': []}
for job in IDS:
    execution = api('/api/scheduler/jobs/' + job, 'POST')['execution_id']
    result['executions'].append(wait_run(job, execution))
# A second Sina execution checks daily deduplication and provides two rows for pagination.
execution = api('/api/scheduler/jobs/' + IDS[1], 'POST')['execution_id']
result['executions'].append(wait_run(IDS[1], execution))
first = api(f'/api/scheduler/jobs/{IDS[1]}/executions?limit=1')[0]
second = api(f'/api/scheduler/jobs/{IDS[1]}/executions?limit=1&offset=1')[0]
assert first['id'] != second['id']
assert api(f'/api/scheduler/jobs/{IDS[1]}/executions?status=failed') == []
assert api(f'/api/scheduler/jobs/{IDS[1]}/executions?status=success')
result['final_jobs'] = [x for x in api('/api/scheduler/jobs') if x['id'] in IDS]
result['sina_records'] = api('/api/adapters/adapter_sina_spot/records?limit=100')
result['latest_futures'] = api('/api/data/latest?topic=corn_futures_price')
assert result['latest_futures'], 'Real futures prices must be visible in latest API'
records = [x for x in result['sina_records'] if x.get('metadata', {}) and x['metadata'].get('is_mock') is False]
assert len(records) == 41, len(records)
assert sum(x['topic_name'] == 'corn_spot_price' for x in records) == 40
assert sum(x['topic_name'] == 'corn_futures_price' for x in records) == 1
path = Path(__file__).resolve().parents[2] / 'docs/reports/day3-manual-evidence.json'
path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print('PASS: two real manual jobs; Sina repeat/dedup; history pagination/filter; latest futures API')
print(json.dumps(result['executions'], ensure_ascii=False, indent=2))
