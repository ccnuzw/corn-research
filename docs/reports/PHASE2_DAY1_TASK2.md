# Phase 2 Day 1 Task 2 - Unified Redis Cursor Management

Completed on 2026-10-22 after Task1 async jobs. Backend image rebuilt and deployed;
standard Compose settings restored after isolated integration tests. No production
cursor was reset. Existing unrelated worktree changes were preserved.

## Implementation

- `collectors-python/cursor.py`: shared CursorManager, positive integer and ISO date
  types, strict validation, monotonic Redis CAS, explicit failures for corrupt or
  unavailable Redis, reusable Redis locks, deferred acknowledgement sessions.
- `collectors-python/collectors/base.py`: optional configure/get/advance cursor
  methods. Collectors without configured cursors retain their previous behavior.
- Boyar delegates cursor access to the shared module without changing its production
  key `collector:boyar:last_article_id`, start-at-last-plus-one rule or scan limits.
- Sina maintains separate spot/futures business-date watermarks. Same-day repeated
  runs return no new observations; a current future cannot hide a later spot report.
  Old dated report links skip HTML fetch. Partial stream/date batches do not advance
  that stream's cursor. Diagnostic incremental=False does not read/write cursors.
- The Python runner stages proposals in cursor_updates. Rust persists/deduplicates
  all returned records before invoking commit_cursors.py. Any rejected insertion
  prevents all proposed acknowledgements. Redis acknowledgement errors fail the run
  so a retry can deduplicate already persisted records and acknowledge again.
- New tests: test_cursor_manager.py, test_sina_cursors.py and the real end-to-end
  backend-rust/tests/cursor_pipeline_api.py. Existing Boyar and Sina tests updated.
  API and collector README describe behavior and compatibility boundaries.

## Test Results

| Verification | Result |
| --- | --- |
| Host Python unittest suite, real Redis isolated keys | 72 passed |
| Final deployed container Python suite, real Redis isolated keys | 72 passed |
| Docker Rust cargo test --locked --offline | 8 passed, 1 ignored |
| Async API suite, including real bounded Boyar and overlap guard | 4 passed |
| Existing API regression | 10 passed |
| Collection history API regression | 5 passed |
| Scheduler controlled-failure persistence | 1 passed |
| Restart scenarios: queued/interrupted/already committed | All 3 passed |
| Real Sina pipeline: failed SQL, successful retry, incremental repeat | Passed |
| Production Sina first/repeated job, normal Compose configuration | 41 then 0 |
| git diff --check | Passed |

The single initially failing container test inherited the deliberately overridden
SINA_CURSOR_KEY while asserting a default key. Its fake-Redis fixture now supplies
an explicit key, and both host and final image suites pass all72 tests.
The ignored Rust test is the pre-existing notification service test, not a cursor test.

Fault injection uses an adapter-scoped PostgreSQL trigger and fresh
test:phase2:sina:* Redis keys, never production keys. All41 rejected observations
produced a failed job; both Redis checkpoints remained absent. After removing the
trigger, the successful job returned41 and acknowledged both dates. Its next run
returned0. Temporary trigger/function/adapter/failed queue row were cleaned up;
isolated Redis keys were deleted after restoring standard deployment settings.

Evidence:
- `docs/reports/phase2-task2-pipeline.json`
- `docs/reports/phase2-task2-async-live.json`
- `docs/reports/phase2-task2-recovery.json`
- `docs/reports/phase2-task2-production.json`

## Production Values And Observations

| Redis key | Verified final value |
| --- | --- |
| collector:boyar:last_article_id | 1267906 |
| collector:sina:last_date | 2026-10-22 |
| collector:sina:last_date:futures | 2026-10-22 |

Boyar's real bounded regression advanced1267904 ->1267906 using a temporary scan
limit2; no target arrival observation was found in those two articles. The standard
limit150 is restored. No claim is made that this was a full Boyar production scan.

Production Sina initial cursor bootstrap:
- Job `1d017485-426e-48d9-9d34-1db39b099e11`, run `b11b34d4-7020-4e78-83e9-527c32f18a80`.
- Returned41 real observations, all already present: new0/duplicates41/failed0.
- Approximately57.5seconds including source latency/retries; cursor confirmed only
  after persistence/deduplication. Existing adapter record count remained81.

Production same-date repeat:
- Job `3aea20e9-be7b-4cee-b1d7-bb3bcdf43f8b`, run `d2f34838-2042-4a7c-9b23-906865a9b5a1`.
- Returned0 in approximately5.4seconds; adapter record count remained81.
- Both jobs succeeded with progress100 and null error_message.

Container corn_backend is running/healthy, restart_count0. GET /health returns200
and `{"success":true,"data":"Corn Backend V2 is running","message":null}`.
No panic appeared; the production verification jobs logged no errors. A subsequent
history regression deliberately invoked __invalid_script__ and logged the expected
ERROR for that controlled failure; this is not a production source/cursor failure.
SINA_CURSOR_KEY and BOYAR_SCAN_LIMIT test overrides are absent. Both seeded scheduled
jobs remain disabled; automatic scheduling is not newly enabled by this task.

## Operational Boundaries

- PostgreSQL and Redis are not one atomic transaction. Crash after SQL writes but
  before acknowledgement can repeat fetches; database deduplication handles retries.
  This closes the previous ahead-of-persistence cursor gap, not exactly-once delivery.
- Direct collector class collect() calls still commit directly. run_collector.py
  outputs proposals only; do not manually acknowledge before consuming/persisting them.
- Legacy Boyar synchronous count-only API does not persist, so no cursor advance.
  Use async collection or adapter run endpoints for production ingestion.
- Sina uses the first daily snapshot, not intraday updates or comprehensive history.
  max_items is not pagination; use a full daily batch, default100. A truncated date
  remains eligible. Stable futures symbol configuration is assumed; adding a symbol
  mid-day needs explicit backfill rather than resetting a production cursor.
- Redis locks cover collection, not the later SQL/ack phase. Overlap can duplicate
  work, but monotonic CAS prevents rewind. Async jobs separately reject active jobs
  for the same adapter. Crashed collector locks expire by their existing lease.
- Single-backend recovery, no automatic replay of interrupted jobs and no new
  authentication/retention policy. These Task1 limitations remain unchanged.

## Verification Commands

```sh
BOYAR_TEST_REDIS_URL=redis://localhost:16380/0 \
  python3 -m unittest discover -s collectors-python/tests -v
docker exec -e BOYAR_TEST_REDIS_URL=redis://redis:6379/0 corn_backend \
  python3 -m unittest discover -s /app/collectors-python/tests -v
docker exec corn_redis redis-cli MGET collector:boyar:last_article_id \
  collector:sina:last_date collector:sina:last_date:futures
curl -fsS http://localhost:18000/health
```

The fault-injection script requires a temporary isolated SINA_CURSOR_KEY beginning
test:phase2:sina: and fresh keys; it deliberately refuses production configuration.
The async live suite requires a temporary BOYAR_SCAN_LIMIT2 to keep the smoke bounded.
Restore standard Compose settings afterward. Restart tests recreate the backend and
must only be run in an appropriate maintenance window.
