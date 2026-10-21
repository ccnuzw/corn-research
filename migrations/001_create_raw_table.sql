-- RAW层表结构
CREATE TABLE IF NOT EXISTS raw_collection_records (
    id UUID PRIMARY KEY,
    collector_id VARCHAR(100) NOT NULL,
    business_date DATE NOT NULL,
    indicator_name VARCHAR(200) NOT NULL,
    value NUMERIC NOT NULL,
    unit VARCHAR(20) NOT NULL,
    region VARCHAR(100),
    
    -- 溯源
    source_url TEXT NOT NULL,
    original_text TEXT,
    
    -- 去重
    dedup_key VARCHAR(500) UNIQUE NOT NULL,
    
    -- 时间戳
    collected_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_raw_indicator_date 
    ON raw_collection_records(indicator_name, business_date DESC);

CREATE INDEX IF NOT EXISTS idx_raw_collector 
    ON raw_collection_records(collector_id, collected_at DESC);

CREATE INDEX IF NOT EXISTS idx_raw_business_date 
    ON raw_collection_records(business_date DESC);

-- 自动更新updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_raw_collection_records_updated_at 
    BEFORE UPDATE ON raw_collection_records 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
