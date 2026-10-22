"""Restart test for single-backend Compose. Seeds only isolated adapters/jobs.
Run after normal async API tests. Recreates backend using the standard Compose config.
"""
import json
from pathlib import Path
import subprocess
import time
from uuid import uuid4
from history_api import request

ROOT = Path(__file__).resolve().parents[2]
jobs, adapters, runs = [], [], []

def sql(statement):
    return subprocess.check_output(['docker', 'exec', 'corn_postgres', 'psql', '-XAt',
        '-v', 'ON_ERROR_STOP=1', '-U', 'corn_user', '-d', 'corn_research', '-c', statement], text=True)

try:
    for case in ('queued', 'interrupted', 'committed'):
        adapter, job, run = 'test_recovery_' + uuid4().hex[:12], str(uuid4()), str(uuid4())
        code, payload = request('/api/adapters', 'POST', {'id': adapter, 'name': case,
            'source_id': 'boyar', 'script_file': 'mock', 'topic_name': 'test_recovery'})
        assert code == 200, payload
        adapters.append(adapter)
        jobs.append(job)
        if case == 'queued':
            # First seed disabled running rows and convert to queued immediately before restart.
            sql(f"INSERT INTO async_jobs(id,collector_name,adapter_id,max_items,status,phase) VALUES('{job}','mock','{adapter}',2,'running','recovery-test');")
        else:
            runs.append(run)
            status = 'running' if case == 'interrupted' else 'success'
            sql(f"BEGIN; INSERT INTO collection_runs(id,adapter_id,started_at,status,records_collected) VALUES('{run}','{adapter}',NOW(),'{status}',2); INSERT INTO async_jobs(id,collector_name,adapter_id,run_id,max_items,status,phase) VALUES('{job}','mock','{adapter}','{run}',2,'running','recovery-test'); COMMIT;")
    # Stop the backend to guarantee the queued seed cannot be consumed before restart.
    subprocess.run(['docker','compose','stop','backend'], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    sql(f"UPDATE async_jobs SET status='queued',phase='queued' WHERE id='{jobs[0]}';")
    subprocess.run(['docker','compose','up','-d','--no-build','--no-deps','--wait','--wait-timeout','90','backend'],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    evidence = []
    for job, expected in zip(jobs, ('succeeded','failed','succeeded')):
        for _ in range(100):
            code, payload = request('/api/jobs/' + job)
            assert code == 200, payload
            row = payload['data']
            if row['status'] in ('succeeded','failed'): break
            time.sleep(.1)
        assert row['status'] == expected, row
        if expected == 'failed': assert 'restarted' in row['error_message'], row
        evidence.append(row)
    (ROOT/'docs/reports/phase2-task1-recovery.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    print('PASS: queued job resumes; interrupted job fails; previously committed run reconciles to success')
finally:
    for job in jobs:
        sql(f"DELETE FROM async_jobs WHERE id='{job}';")
    for adapter in adapters:
        code, payload = request('/api/adapters/' + adapter, 'DELETE')
        assert code == 200, payload
