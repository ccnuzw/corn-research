-- Distinguish enterprises/contracts without changing legacy adapters' daily deduplication.
BEGIN;
ALTER TABLE collection_records ADD COLUMN IF NOT EXISTS record_key TEXT NOT NULL DEFAULT '';
ALTER TABLE collection_records ADD COLUMN IF NOT EXISTS indicator TEXT;
ALTER TABLE collection_records ADD COLUMN IF NOT EXISTS region TEXT;
ALTER TABLE collection_records ADD COLUMN IF NOT EXISTS metadata JSONB;
ALTER TABLE collection_records DROP CONSTRAINT IF EXISTS collection_records_adapter_id_business_date_topic_name_key;
CREATE UNIQUE INDEX IF NOT EXISTS idx_collection_record_series
    ON collection_records(adapter_id, business_date, topic_name, record_key);
UPDATE adapters SET name = '新浪财经-玉米现货及期货价格', updated_at = NOW()
    WHERE id = 'adapter_sina_spot' AND script_file = 'sina_production';
INSERT INTO sources(id, name, domain, description, status)
VALUES ('sina', '新浪财经', 'finance.sina.com.cn', '玉米现货报告与期货报价，不提供北方四港数据', 'active')
ON CONFLICT (id) DO NOTHING;
INSERT INTO adapters(id, name, script_file, source_id, topic_name)
VALUES ('adapter_sina_spot', '新浪财经-玉米现货及期货价格', 'sina_production', 'sina', 'corn_spot_price')
ON CONFLICT (id) DO NOTHING;
COMMIT;
