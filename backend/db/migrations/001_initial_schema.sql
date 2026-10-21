-- 初始化TimescaleDB扩展
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 价格表（时序表）
CREATE TABLE IF NOT EXISTS prices (
    time TIMESTAMPTZ NOT NULL,
    commodity VARCHAR(50) NOT NULL,
    location VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    price_type VARCHAR(50),
    source VARCHAR(100),
    source_url TEXT,
    quality_score DECIMAL(3, 2),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (time, commodity, location, source)
);

-- 转换为时序表
SELECT create_hypertable('prices', 'time', if_not_exists => TRUE);

-- 创建连续聚合（日均价）
CREATE MATERIALIZED VIEW IF NOT EXISTS prices_daily
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', time) AS day,
    commodity,
    location,
    AVG(price) as avg_price,
    MAX(price) as max_price,
    MIN(price) as min_price,
    COUNT(*) as sample_count
FROM prices
GROUP BY day, commodity, location;

-- 基本面指标表（时序表）
CREATE TABLE IF NOT EXISTS fundamentals (
    time TIMESTAMPTZ NOT NULL,
    indicator VARCHAR(100) NOT NULL,
    value DECIMAL(15, 2) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    frequency VARCHAR(20),
    source VARCHAR(100),
    source_url TEXT,
    quality_score DECIMAL(3, 2),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (time, indicator, source)
);

SELECT create_hypertable('fundamentals', 'time', if_not_exists => TRUE);

-- 期货数据表
CREATE TABLE IF NOT EXISTS futures (
    time TIMESTAMPTZ NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    contract VARCHAR(50) NOT NULL,
    price_open DECIMAL(10, 2),
    price_high DECIMAL(10, 2),
    price_low DECIMAL(10, 2),
    price_close DECIMAL(10, 2) NOT NULL,
    volume INTEGER,
    open_interest INTEGER,
    source VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (time, exchange, contract)
);

SELECT create_hypertable('futures', 'time', if_not_exists => TRUE);

-- 数据源表
CREATE TABLE IF NOT EXISTS sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL,
    url TEXT,
    reliability_score DECIMAL(3, 2),
    last_success_at TIMESTAMPTZ,
    failure_count INTEGER DEFAULT 0,
    config JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 采集日志表
CREATE TABLE IF NOT EXISTS collection_logs (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL,
    records_collected INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 用户偏好表
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) UNIQUE NOT NULL,
    theme VARCHAR(50) DEFAULT 'tech-blue',
    default_location VARCHAR(100),
    favorite_indicators TEXT[],
    alert_config JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_prices_location_time ON prices (location, time DESC);
CREATE INDEX IF NOT EXISTS idx_prices_quality ON prices (quality_score) WHERE quality_score >= 0.7;
CREATE INDEX IF NOT EXISTS idx_fundamentals_indicator_time ON fundamentals (indicator, time DESC);
CREATE INDEX IF NOT EXISTS idx_collection_logs_source_time ON collection_logs (source_id, started_at DESC);

-- 初始数据源
INSERT INTO sources (name, type, url, reliability_score) VALUES
    ('博亚和讯', 'public_media', 'https://m.boyar.cn', 0.75),
    ('新浪财经', 'public_media', 'https://finance.sina.com.cn', 0.80),
    ('大商所', 'official_exchange', 'http://www.dce.com.cn', 1.00),
    ('国家统计局', 'official_government', 'http://data.stats.gov.cn', 1.00)
ON CONFLICT (name) DO NOTHING;
