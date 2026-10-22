# Day 3 Sina Collector - Option A

The generic futures homepage has no north-port table. Following the approved
Option A, the collector now obtains real corn spot and futures prices instead.
Random north-port mock fallback and placeholder third-party URLs were removed.

## Implementation and Tests

- Corn channel discovery restricted to dated Sina corn report links. Newest report
  first, at most five candidates; only the corn processor price table is accepted.
- Strict observation dates and positive finite prices; malformed/missing schemas
  raise errors, never synthetic records. Soybean-meal tables are excluded.
- Every network attempt is paced 1..3 seconds with rotating User-Agent and Referer.
- Initial attempt plus up to three retries, exponential waits 1/2/4 seconds;
  transport errors,408,429,5xx retry, permanent403/404 do not.
- 14 offline unit tests passed; all Python tests45 passed inside the deployed image.
- Real backend scheduler manually ran Sina twice: 41 rows on each fetch, first
  inserted41, second inserted0/duplicates41, failures0. Collection and legacy raw
  tables both receive the same per-series observations atomically per record.
- Spot40 / futures1. Full real samples: `day3-sina-samples.json`.
- Futures topic works in latest-data API; full series metadata lives in adapter
  records. Dates are source observation dates, not the test-run date.

## Production Boundaries

`nf_C0` is continuous, not a deliverable contract. Other corn contracts can be
configured using SINA_FUTURES_SYMBOLS. This is a first-daily-snapshot collector,
not a tick feed; repeat quotes do not overwrite the first observation that day.
Enterprise moisture/quality labels are preserved without national-price normalization.
Failure of either required source fails the batch; there is no partial success fallback.
Changes in report titles/table format require parser maintenance. There is no
north-port inventory/shipping output.

Quality B is stored in collection_records. Legacy latest-data responses still
hardcode A; fixing that pre-existing projection is a Day 4 item.

## Integration

Apply migration007 before running the new backend. Aliases sina/sina_production
and adapter_sina_spot remain compatible. Both Sina collector-name triggers and
adapter triggers persist data. New uniqueness includes the enterprise/contract key,
so forty different enterprise observations on one date are not collapsed together.

Files: collectors-python/collectors/sina_production.py,
collectors-python/tests/test_sina_production.py, migrations/007_sina_corn_prices.sql,
backend-rust/src/collection_execution.rs, backend-rust/src/db/collection_entities.rs,
backend-rust/src/collection_handlers.rs, backend-rust/src/handlers.rs, docs/API.md.
