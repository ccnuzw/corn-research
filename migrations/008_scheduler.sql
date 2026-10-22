BEGIN;
CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    collector_id TEXT NOT NULL,
    cron_expression TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'idle' CHECK (status IN ('idle','running','success','failed')),
    last_run TIMESTAMPTZ,
    last_error TEXT,
    total_runs BIGINT NOT NULL DEFAULT 0,
    success_count BIGINT NOT NULL DEFAULT 0,
    failed_count BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS job_executions (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES scheduled_jobs(id) ON DELETE CASCADE,
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('scheduled','manual')),
    status TEXT NOT NULL CHECK (status IN ('running','success','failed')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    records_collected INTEGER NOT NULL DEFAULT 0,
    collection_run_id TEXT,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_job_execution_history ON job_executions(job_id, started_at DESC, id DESC);
-- Scheduler 0.9 evaluates cron in UTC. These are 08:00 and 09:00 Asia/Shanghai.
-- Examples remain disabled until Day 4 automatic-scheduling validation; manual trigger is allowed.
INSERT INTO scheduled_jobs(id,name,collector_id,cron_expression,description,enabled) VALUES
('89000000-0000-4000-8000-000000000001','博亚每日采集','boyar_production','0 0 0 * * *','每天北京时间08:00 / UTC 00:00',false),
('89000000-0000-4000-8000-000000000002','新浪玉米每日采集','sina_production','0 0 1 * * *','每天北京时间09:00 / UTC 01:00',false)
ON CONFLICT (id) DO NOTHING;
COMMIT;
