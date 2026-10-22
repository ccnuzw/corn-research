-- Fetched count is distinct from newly persisted records (legacy run API is fetch-only).
ALTER TABLE collection_runs
    ADD COLUMN IF NOT EXISTS records_collected INTEGER NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_runs_adapter_started
    ON collection_runs (adapter_id, started_at DESC, id DESC);
