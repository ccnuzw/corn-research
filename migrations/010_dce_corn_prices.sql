BEGIN;
INSERT INTO sources(id, name, domain, description, status)
VALUES ('dce', '大连商品交易所', 'www.dce.com.cn', '官方日行情：玉米合约收盘价/结算价；不使用合成价格', 'active')
ON CONFLICT (id) DO NOTHING;
INSERT INTO adapters(id, name, script_file, source_id, topic_name)
VALUES ('adapter_dce_futures', '大商所-玉米期货日行情', 'dce_production', 'dce', 'corn_futures_price')
ON CONFLICT (id) DO NOTHING;
COMMIT;
