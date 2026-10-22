BEGIN;
CREATE TABLE IF NOT EXISTS async_jobs (
    id UUID PRIMARY KEY,
    collector_name TEXT NOT NULL,
    adapter_id VARCHAR(50) NOT NULL REFERENCES adapters(id) ON DELETE RESTRICT,
    run_id VARCHAR(50) REFERENCES collection_runs(id) ON DELETE SET NULL,
    max_items INTEGER NOT NULL CHECK (max_items BETWEEN 1 AND 1000),
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','succeeded','failed')),
    progress INTEGER NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    phase TEXT NOT NULL DEFAULT 'queued',
    details JSONB NOT NULL DEFAULT '{}',
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_async_jobs_queue ON async_jobs(created_at,id) WHERE status='queued';
CREATE UNIQUE INDEX IF NOT EXISTS idx_async_jobs_active_adapter ON async_jobs(adapter_id)
    WHERE status IN ('queued','running');
COMMIT;
