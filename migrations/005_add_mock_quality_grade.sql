-- 添加Mock数据质量等级支持
-- 修复问题：Mock测试数据应该明确标识，不应混入正常质量评级

-- 1. 修改quality_grade约束，添加'M' (MOCK)
ALTER TABLE market_facts_standard 
DROP CONSTRAINT IF EXISTS market_facts_standard_quality_grade_check;

ALTER TABLE market_facts_standard 
ADD CONSTRAINT market_facts_standard_quality_grade_check 
CHECK (quality_grade IN ('A', 'B', 'C', 'D', 'M'));

-- 2. 更新高质量数据视图，排除Mock数据
CREATE OR REPLACE VIEW market_facts_standard_quality AS
SELECT * FROM market_facts_standard
WHERE is_latest = TRUE 
  AND quality_grade IN ('A', 'B')
  AND quality_grade != 'M';  -- 排除Mock数据

-- 3. 创建专门的Mock数据视图
CREATE OR REPLACE VIEW market_facts_standard_mock AS
SELECT * FROM market_facts_standard
WHERE is_latest = TRUE 
  AND quality_grade = 'M';

-- 4. 更新注释
COMMENT ON COLUMN market_facts_standard.quality_grade IS '质量等级：A=优秀 B=良好 C=一般 D=较差 M=Mock测试数据';

COMMENT ON VIEW market_facts_standard_quality IS '高质量数据视图：仅包含A/B级真实数据，排除Mock';
COMMENT ON VIEW market_facts_standard_mock IS 'Mock测试数据视图：用于开发和测试';
