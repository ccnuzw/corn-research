# Phase 1 Day 3 Task 2 - Simplified Scheduler Report

Date: 2026-10-22 (Asia/Shanghai). Selected scope: Option A.

## Completed

- Created and verified PostgreSQL `scheduled_jobs` and `job_executions` tables.
- Added two idempotent example schedules (migration 008):
  - Boyar: Beijing 08:00, UTC cron `0 0 0 * * *`.
  - Sina: Beijing 09:00, UTC cron `0 0 1 * * *`.
- Both examples remain disabled. Manual triggering is permitted; automatic operation
  is not claimed as verified or enabled.
- Replaced the fixed simulated result (42) with the real collector execution and
  persistence service. Manual results link to actual `collection_runs` rows.
- Added execution-history querying and persisted job status/counters.

## Live Verification

Real HTTP triggers, not mocked scheduler execution:

| Collector | Result | Collected | New | Duplicates | Failed |
| --- | --- | ---: | ---: | ---: | ---: |
| Boyar | success | 0 | 0 | 0 | 0 |
| Sina first run | success | 41 | 41 | 0 | 0 |
| Sina second run | success | 41 | 0 | 41 | 0 |

Boyar smoke test used a temporary Compose override `BOYAR_SCAN_LIMIT=2`, processed
article IDs 1267751..1267752, and advanced the production Redis checkpoint from
1267750 to **1267752**. Neither page matched the target metric: zero records is an
honest successful no-target result, not a claim of new arrivals data.
The temporary override was removed after testing; normal scan_limit150 is restored.

Sina persisted 40 enterprise corn spot quotes and one continuous futures quote.
The repeat did not create extra rows. Futures filtering in `/api/data/latest` works.
History querying, `limit=1&offset=1` pagination and status filtering passed.

Evidence: `day3-manual-evidence.json` contains execution IDs, timestamps, job states,
record samples and API results. Reproduction script:
`backend-rust/tests/scheduler_manual.py` (run Boyar with a bounded scan when testing).

Other regression checks: Python collector tests **45/45**, API tests **10/10**,
collection-history tests **5/5**. Docker build and deployment passed.

## Final Scope Verification

- Rechecked Boyar's persisted successful manual execution and its collection-run link.
- Re-triggered the real Sina example successfully; the final execution is captured in
  `day3-task2-final-verification.json`.
- Added and ran `backend-rust/tests/scheduler_failure.py`: **1/1 passed**.
  It creates an isolated disabled job/adapter referencing a deliberately unknown
  Python collector, then manually triggers it. The actual runner returns
  `Unknown collector: __scheduler_failure_probe_...`.
- Confirmed `job_executions.status=failed`, non-empty `error_message`, completed_at,
  scheduled_jobs.last_error and failed_count, and the linked failed collection run.
  An independent PostgreSQL SELECT confirmed the same persisted error, not just an
  API response. Snapshot: `day3-scheduler-failure-evidence.json`.
- Removed the isolated job/adapter after capturing evidence. Their failure rows are
  removed by cascade; exactly the two original disabled examples remain. This
  controlled failure is not a failure of either production collector.

The requested simplified scope is complete: success/failure manual execution,
database history verification, error_message verification, and operating notes.
No additional backend code or image rebuild was required for this final verification.

## Manual Operation

Run from a terminal on the backend host. POST returns an asynchronous execution_id;
poll the history until that execution becomes success or failed.

```sh
# List both examples (disabled means no automatic execution, not no manual execution).
curl -fsS http://localhost:18000/api/scheduler/jobs

# Boyar: Beijing 08:00 example. Normal runs can scan up to 150 articles.
curl -fsS -X POST http://localhost:18000/api/scheduler/jobs/89000000-0000-4000-8000-000000000001

# Sina: Beijing 09:00 example.
curl -fsS -X POST http://localhost:18000/api/scheduler/jobs/89000000-0000-4000-8000-000000000002

# Read history; optional status=failed filters errors, limit/offset paginate.
curl -fsS 'http://localhost:18000/api/scheduler/jobs/89000000-0000-4000-8000-000000000002/executions?limit=20&offset=0'

# Reproduce the isolated failure test; it cleans up its own job and adapter.
python3 backend-rust/tests/scheduler_failure.py
```

Do not enable automatic runs yet. The configured UTC cron expressions correspond
to Beijing 08:00 and 09:00; automatic timing is still a Day 4 validation item.

## Day 4 / Explicitly Deferred

- Automatic timing verification and enabling the example schedules.
- Full failure-notification testing and delivery reliability.
- Cron update API (currently HTTP501), retention and missed-run catch-up policy.
- Multi-backend restart/leadership safety; current recovery assumes one backend.
- Legacy latest-data quality projection still hardcodes A; Sina adapter records
  correctly store B and include source/series metadata.

## Changed Files

- `migrations/008_scheduler.sql`
- `backend-rust/src/scheduler/job_manager.rs`
- `backend-rust/src/main.rs`
- `backend-rust/tests/scheduler_manual.py`
- `backend-rust/tests/scheduler_failure.py`
- `docs/API.md`
- `docs/reports/day3-manual-evidence.json`
- `docs/reports/day3-scheduler-failure-evidence.json`
- `docs/reports/day3-task2-final-verification.json`

No unrelated frontend modifications were reverted. No commit was created.
