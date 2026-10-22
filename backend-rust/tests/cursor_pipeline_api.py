"""Real Sina pipeline, with isolated Redis keys and an adapter-scoped DB failure.
Requires backend SINA_CURSOR_KEY=test:phase2:sina:<unique>; never resets production cursors.
"""
import json
from pathlib import Path
import subprocess
import time
from uuid import uuid4
from history_api import request


def sql(statement):
    return subprocess.check_output(['docker','exec','corn_postgres','psql','-XAt','-v','ON_ERROR_STOP=1',
        '-U','corn_user','-d','corn_research','-c',statement],text=True).strip()


def redis_get(key):
    value = subprocess.check_output(['docker','exec','corn_redis','redis-cli','--raw','GET',key],text=True).strip()
    return value or None


def api(path, method='GET', body=None, expected=200):
    status, result = request(path, method, body)
    assert status == expected and result['success'], (status,result)
    return result['data']


def wait(job):
    for _ in range(360):
        row = api('/api/jobs/' + job)
        if row['status'] in ('succeeded','failed'):return row
        time.sleep(.5)
    raise AssertionError('Job timed out: ' + job)


env = json.loads(subprocess.check_output(['docker','inspect','corn_backend','--format','{{json .Config.Env}}'],text=True))
key = next(x.split('=',1)[1] for x in env if x.startswith('SINA_CURSOR_KEY='))
assert key.startswith('test:phase2:sina:'), 'Refuse fault injection with production cursor keys'
assert redis_get(key) is None and redis_get(key+':futures') is None, 'Use fresh isolated test keys'
adapter, bad_job = 'test_cursor_pipeline_' + uuid4().hex[:10], str(uuid4())
function = 'test_cursor_reject_' + uuid4().hex[:10]
evidence = {'cursor_key':key,'mode':'live Sina; isolated Redis keys; adapter-scoped PostgreSQL rejection'}
try:
    api('/api/adapters','POST',{'id':adapter,'name':'Isolated cursor pipeline failure',
        'source_id':'sina','script_file':'sina_production','topic_name':'corn_spot_price'})
    sql(f"CREATE FUNCTION {function}() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.adapter_id='{adapter}' THEN RAISE EXCEPTION 'controlled cursor-persistence test'; END IF; RETURN NEW; END $$; CREATE TRIGGER {function} BEFORE INSERT ON collection_records FOR EACH ROW EXECUTE FUNCTION {function}();")
    # Insert a test queue row directly to avoid ambiguous name resolution while two
    # adapters temporarily use the same script. The worker path is unmodified.
    sql(f"INSERT INTO async_jobs(id,collector_name,adapter_id,max_items) VALUES('{bad_job}','sina_production','{adapter}',100);")
    row = wait(bad_job)
    assert row['status']=='failed' and 'failed validation or insertion' in row['error_message'], row
    assert redis_get(key) is None and redis_get(key+':futures') is None
    evidence['persistence_failure_job'] = row
    evidence['checkpoint_after_failed_persistence'] = [redis_get(key),redis_get(key+':futures')]
finally:
    sql(f'DROP TRIGGER IF EXISTS {function} ON collection_records; DROP FUNCTION IF EXISTS {function}();')
    sql(f"DELETE FROM async_jobs WHERE id='{bad_job}' AND status IN ('succeeded','failed');")
    api('/api/adapters/'+adapter,'DELETE')

runs=[]
for index in range(2):
    accepted=api('/api/collectors/run/async','POST',{'collector_name':'sina_production'},expected=202)
    row=wait(accepted['job_id'])
    assert row['status']=='succeeded',row
    assert row['result']['records_collected']==(41 if index==0 else 0),row
    runs.append(row)
    assert redis_get(key)=='2026-10-22' and redis_get(key+':futures')=='2026-10-22'
evidence['successful_jobs']=runs
evidence['checkpoint_after_success']=[redis_get(key),redis_get(key+':futures')]
path=Path(__file__).resolve().parents[2]/'docs/reports/phase2-task2-pipeline.json'
path.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
print('PASS: DB failure preserves cursor; persisted success advances; second run returns zero new observations')
