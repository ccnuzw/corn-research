# Phase 2 Day 1 Task 1 - Async Collector Jobs

## Delivered

- Migration009 creates a durable async_jobs queue and an active-adapter uniqueness
  guard. Apply it before starting the new backend.
- POST `/api/collectors/run/async` validates and enqueues without waiting for Python;
  returns HTTP202 with job_id/status_url. GET `/api/jobs/:id` exposes durable state,
  phase, monotonic progress, result, errors, timestamps and collection run_id.
- Two fixed workers claim jobs transactionally using FOR UPDATE SKIP LOCKED. Actual
  collection uses the existing history and persistence lifecycle. Same-adapter
  queued/running duplicates return409. Existing synchronous endpoints are unchanged.
- Opt-in Python stderr progress is streamed while the child runs. Stdout remains
  record JSON. Scanning is5..85%, collected88%, persisting90%; only successful run
  finalization reaches100%. Failed jobs retain their last real progress.
- Process execution has a two-hour cap and kill-on-drop for async child processes.
- Queued jobs survive restart. Running jobs are reconciled from their collection run:
  an already successful run is recognized; interrupted runs fail with an explanation.
  There is no automatic retry of interrupted site scans.

## Verification

- Python unit suite55 passed (includes actual Redis integration with isolated keys).
- Async live API4 passed: fast202 response (<2s), state/results/history, validation,
  controlled Python failure, real bounded Boyar execution, progress and overlap409.
- Boyar job `1ddfbfbb-9bf7-429a-af31-ae4fee2239df` completed in the background in
  approximately5.3seconds with a temporary scan_limit2. No target records were found;
  zero is an honest result, not mock success. Evidence: phase2-task1-live.json.
- Observed progress0 ->1 ->5 ->45 ->88 ->100; API polling continued during collection.
- Restart tests passed for queued resume, interrupted failure, and already committed
  run reconciliation; evidence: phase2-task1-recovery.json. Isolated test rows cleaned.
- Existing API regression10 and collection-history5 passed after container recreation.
- Restart test restored the standard Compose configuration (normal Boyar scan_limit150).

## Usage

```sh
curl -fsS -X POST http://localhost:18000/api/collectors/run/async \
  -H 'Content-Type: application/json' \
  -d '{"collector_name":"boyar_production","max_items":100}'
curl -fsS http://localhost:18000/api/jobs/JOB_UUID
```

Statuses: queued, running, succeeded, failed. A202 response means accepted, not
completed. max_items1..1000 limits returned records, not the number of scanned
articles. Progress is phase/work-budget based, not a prediction of remaining time.

## Boundaries

Single-backend Compose recovery only; no multi-instance leadership or cancellation
API. No authentication was added to the existing unauthenticated service. The active
job guard covers this async queue; legacy/scheduler triggers may still contend, with
Boyar's Redis lock preventing simultaneous incremental scans. Queue has no retention
policy or user quotas yet. PostgreSQL and Redis updates are not one transaction.
At Task1 delivery, Python could commit the cursor before backend persistence; Task2
replaces that behavior with staged cursor proposals and acknowledgement only after
all returned records persist. See PHASE2_DAY1_TASK2.md for fault-injection evidence
and remaining retry/atomicity limits. Running jobs are never silently replayed after
a restart. The task1-live/recovery JSON files are also refreshed by later regression
runs; Task2 preserves its own copies under phase2-task2-*.json.
