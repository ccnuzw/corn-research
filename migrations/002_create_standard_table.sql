-- STANDARD层表结构
-- 数据持久化链路：RAW → STANDARD
CREATE TABLE IF NOT EXISTS market_facts_standard (
    id UUID PRIMARY KEY,
    
    -- 业务字段
    business_date DATE NOT NULL,
    indicator_name VARCHAR(100) NOT NULL,
    value NUMERIC(18,4) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    region VARCHAR(50),
    
    -- 质量评分
    quality_grade CHAR(1) NOT NULL CHECK (quality_grade IN ('A', 'B', 'C', 'D')),
    quality_score NUMERIC(5,2),
    quality_issues JSONB,  -- 质量问题列表
    
    -- 数据血统
    source_id VARCHAR(50) NOT NULL,  -- 来源标识
    raw_record_id UUID REFERENCES raw_collection_records(id),  -- 原始记录ID
    
    -- 时间戳
    collected_at TIMESTAMPTZ NOT NULL,      -- 原始采集时间
    standardized_at TIMESTAMPTZ NOT NULL,   -- 标准化时间
    
    -- 版本管理
    version INT DEFAULT 1,
    is_latest BOOLEAN DEFAULT TRUE,
    
    -- 元数据
    metadata JSONB,
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 唯一约束（同一业务日期+指标+来源只保留最新版本）
    UNIQUE(business_date, indicator_name, source_id, version)
);

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_standard_indicator_date 
    ON market_facts_standard(indicator_name, business_date DESC);

CREATE INDEX IF NOT EXISTS idx_standard_quality 
    ON market_facts_standard(quality_grade, business_date DESC);

CREATE INDEX IF NOT EXISTS idx_standard_source 
    ON market_facts_standard(source_id, business_date DESC);

CREATE INDEX IF NOT EXISTS idx_standard_latest 
    ON market_facts_standard(is_latest, business_date DESC) 
    WHERE is_latest = TRUE;

CREATE INDEX IF NOT EXISTS idx_standard_raw_id 
    ON market_facts_standard(raw_record_id);

-- 自动更新updated_at
CREATE TRIGGER update_market_facts_standard_updated_at 
    BEFORE UPDATE ON market_facts_standard 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- 视图：仅最新版本数据
CREATE OR REPLACE VIEW market_facts_standard_latest AS
SELECT * FROM market_facts_standard
WHERE is_latest = TRUE;

-- 视图：高质量数据（A/B级）
CREATE OR REPLACE VIEW market_facts_standard_quality AS
SELECT * FROM market_facts_standard
WHERE is_latest = TRUE 
  AND quality_grade IN ('A', 'B');

COMMENT ON TABLE market_facts_standard IS 'STANDARD层：清洗标准化后的市场数据';
COMMENT ON COLUMN market_facts_standard.quality_grade IS '质量等级：A=优秀 B=良好 C=一般 D=较差';
COMMENT ON COLUMN market_facts_standard.quality_score IS '质量分数：0-100';
COMMENT ON COLUMN market_facts_standard.raw_record_id IS '血统追溯：原始记录ID';
COMMENT ON COLUMN market_facts_standard.version IS '版本号：同一数据被多次更新时递增';
COMMENT ON COLUMN market_facts_standard.is_latest IS '是否最新版本';
