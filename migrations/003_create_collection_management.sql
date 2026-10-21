-- 采集管理系统 - 简化版
-- 创建时间: 2026-10-21

-- 1. 数据源表
CREATE TABLE IF NOT EXISTS sources (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    domain VARCHAR(200),
    description TEXT,
    status VARCHAR(20) DEFAULT 'active',  -- active/inactive
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 采集适配器表
CREATE TABLE IF NOT EXISTS adapters (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    script_file VARCHAR(200) NOT NULL,     -- Python脚本文件名
    source_id VARCHAR(50) NOT NULL,        -- 关联数据源
    topic_name VARCHAR(100) NOT NULL,      -- 采集的数据主题
    status VARCHAR(20) DEFAULT 'stopped',  -- running/stopped/error
    
    -- 增量更新配置（自动管理）
    last_run_at TIMESTAMPTZ,
    last_cursor VARCHAR(200),              -- 最后采集位置
    
    -- 统计信息
    total_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    last_error TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
);

-- 3. 采集记录表（简化的RAW+STANDARD合并）
CREATE TABLE IF NOT EXISTS collection_records (
    id VARCHAR(50) PRIMARY KEY,
    adapter_id VARCHAR(50) NOT NULL,
    
    -- 业务数据
    business_date DATE NOT NULL,
    value DECIMAL(20, 4),
    unit VARCHAR(20),
    topic_name VARCHAR(100),
    
    -- 溯源信息
    source_url TEXT,
    source_html_path TEXT,                 -- 原始HTML存储路径
    
    -- 质量信息（自动评估）
    quality_grade CHAR(1),                 -- A/B/C/D
    quality_score INTEGER,
    
    -- 时间信息
    collected_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    FOREIGN KEY (adapter_id) REFERENCES adapters(id) ON DELETE CASCADE,
    UNIQUE (adapter_id, business_date, topic_name)  -- 防重复
);

-- 4. 采集运行历史表
CREATE TABLE IF NOT EXISTS collection_runs (
    id VARCHAR(50) PRIMARY KEY,
    adapter_id VARCHAR(50) NOT NULL,
    
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status VARCHAR(20),                    -- success/failed/running
    
    -- 统计
    new_records INTEGER DEFAULT 0,
    duplicate_records INTEGER DEFAULT 0,
    failed_records INTEGER DEFAULT 0,
    
    -- 游标信息
    start_cursor VARCHAR(200),
    end_cursor VARCHAR(200),
    
    error_message TEXT,
    
    FOREIGN KEY (adapter_id) REFERENCES adapters(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_adapters_source ON adapters(source_id);
CREATE INDEX IF NOT EXISTS idx_adapters_status ON adapters(status);
CREATE INDEX IF NOT EXISTS idx_adapters_topic ON adapters(topic_name);

CREATE INDEX IF NOT EXISTS idx_records_adapter ON collection_records(adapter_id);
CREATE INDEX IF NOT EXISTS idx_records_date ON collection_records(business_date DESC);
CREATE INDEX IF NOT EXISTS idx_records_topic ON collection_records(topic_name);
CREATE INDEX IF NOT EXISTS idx_records_quality ON collection_records(quality_grade);

CREATE INDEX IF NOT EXISTS idx_runs_adapter ON collection_runs(adapter_id);
CREATE INDEX IF NOT EXISTS idx_runs_started ON collection_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_status ON collection_runs(status);

-- 自动更新updated_at触发器
CREATE TRIGGER update_sources_updated_at 
    BEFORE UPDATE ON sources 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_adapters_updated_at 
    BEFORE UPDATE ON adapters 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- 插入示例数据源
INSERT INTO sources (id, name, domain, description, status) VALUES
    ('boyar', '博亚和讯', 'boyahexun.com', '博亚和讯农产品数据平台', 'active'),
    ('sina', '新浪财经', 'sina.com.cn', '新浪财经农产品频道', 'active'),
    ('dce', '大商所', 'dce.com.cn', '大连商品交易所官网', 'active')
ON CONFLICT (id) DO NOTHING;
