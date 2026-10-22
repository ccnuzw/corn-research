# Phase 1 P1 Release Fixes

Date: 2026-10-22 (Asia/Shanghai).

## Bug 1: Intermittent Sina table discovery failure

Root cause reproduced using the same live corn-channel URL and different User-Agent
headers. The old rotation pool included an iPhone browser. Sina returned a 2,496-byte
CBOT mobile application shell, with no eligible article links, instead of the
75,357-byte domestic corn news channel returned to desktop browsers. Consequently,
the error could disappear on the next run without an upstream HTML change.
Captured response diagnosis: `p1-sina-source-diagnosis.json`.

Fixes in `collectors-python/collectors/sina_production.py`:

- Rotate desktop User-Agent strings only, preserving Referer, pacing and retries.
- Prefer known processor-price reports over generic corn-price articles on the
  same day. Link discovery also accepts title attributes/truncated date labels,
  while restricting source host, path, article suffix and dated article URLs.
- If the corn index has no candidates, try the real Sina futures index once.
- Accept bounded title/body selector alternatives and known processor-header
  variations, including whitespace and full-width unit slashes.
- Skip a bad/unavailable candidate and try the next (maximum five); retain strict
  explicit business dates, two-column corn-table validation and no mock fallback.
- Log response/final URLs, sizes, attempts, page title, candidate/table/record
  counts and rejection causes. Exhausted errors include candidate URLs and reasons.
- A malformed optional publication timestamp is logged, not substituted for the
  report's explicit business date.

The real output remains enterprise spot prices and continuous corn futures quotes,
not north-port inventory. No fabricated fixture values are written to production.

## Bug 2: Panic-prone critical paths

- `handlers.rs`: replace optional latest-timestamp unwrap with iterator max;
  propagate numeric conversion failures instead of silently returning zero; validate
  date-range inputs and use checked date arithmetic to prevent overflow panic.
- `collection_execution.rs`: audit found no direct unwrap/expect in the current
  implementation. Replace positional adapter removal with fallible iterator
  selection. Database transactions, inserts, run finalization and Redis-facing
  Python errors already propagate Results and remain intact.
- `main.rs`: replace database/Redis/scheduler startup expects and listener/server
  unwraps with contextual errors. Log failure and return exit code1 instead of
  panicking. Scheduler JSON serialization errors now produce HTTP500.
- `python_bridge.rs`: pass script PathBuf directly to Command, removing UTF-8
  conversion unwraps; surface Python diagnostic stderr for success and failure.
- Remaining unwraps in handlers.rs are confined to `#[cfg(test)]` assertions.
  `unwrap_or`/`unwrap_or_else` defaults do not panic and are not mechanically removed.
- `.dockerignore`: exclude nested Rust target directories from the build context;
  the previous context included approximately1.5GB of host build artifacts.

## Verification Notes

- An isolated container with invalid DATABASE_URL exits1, logs a startup error and
  has no panic. It has no network and does not touch the production database.
- Initial live release test used a30-second HTTP-client timeout; a transient source
  TLS/read timeout exceeded that client limit. The detached backend task continued
  and succeeded with41 records. Final real-source tests allow180seconds, preserving
  the collector's bounded network retry behavior; instant responses are not promised.
- No scheduled job was enabled. Unrelated frontend changes were preserved.

## Final Deployed Results

- Python collector tests: **53 passed** in the final backend image.
- API regression: **10 passed**; collection-history: **5 passed**.
- P1 live release regression: **3 passed**, including three real Sina API calls,
  each returning41records and a successful run with failed_records0.
- Isolated scheduler failure regression: **1 passed**; expected failure logs are
  present from that deliberate test, not a production source outage.
- Docker Rust tests: **7 passed,1ignored** (existing Redis integration test).
- Invalid-database startup probe on the final image: exit1, no panic.
- Backend: running/healthy, restart_count0; /health HTTP200; no panic in final logs.
- Live acceptance response:

```json
{"success":true,"data":{"collector_id":"sina_production","records_collected":41,"run_id":"ff65088e-5766-4c7f-8bdb-f65ab016118c"},"message":"Collected 41 records"}
```

Full run/history/image evidence: `p1-release-evidence.json`.

## Reproduction

```sh
BOYAR_TEST_REDIS_URL=redis://localhost:16380/0 python3 -m unittest discover -s collectors-python/tests -v
python3 backend-rust/tests/api_regression.py
python3 backend-rust/tests/history_api.py
python3 backend-rust/tests/p1_release_regression.py
python3 backend-rust/tests/scheduler_failure.py
curl -fsS -X POST http://localhost:18000/api/collectors/run \
  -H 'Content-Type: application/json' -d '{"collector_name":"sina_production"}'
```

Python requires the project's installed collector dependencies. The release test
calls the real Sina collector three times; source connectivity is required.
