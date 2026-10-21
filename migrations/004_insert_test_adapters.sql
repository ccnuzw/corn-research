-- 插入测试适配器
INSERT INTO adapters (id, name, script_file, source_id, topic_name, status, total_runs, successful_runs, failed_runs, created_at, updated_at) 
VALUES
    ('adapter_boyar_arrivals', '博亚和讯-山东到车', 'boyar_production', 'boyar', 'corn_arrivals', 'stopped', 0, 0, 0, NOW(), NOW()),
    ('adapter_sina_spot', '新浪财经-现货报价', 'sina_production', 'sina', 'corn_spot_price', 'stopped', 0, 0, 0, NOW(), NOW()),
    ('adapter_mock_test', 'Mock测试采集器', 'mock', 'boyar', 'test_data', 'stopped', 0, 0, 0, NOW(), NOW())
ON CONFLICT (id) DO UPDATE 
SET 
    name = EXCLUDED.name,
    script_file = EXCLUDED.script_file,
    updated_at = NOW();
