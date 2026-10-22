# Mock数据质量标记修复报告

## 任务概述
**优先级**: P3  
**完成时间**: 2026-10-22  
**状态**: ✅ 已完成

## 问题描述
Mock测试数据被标记为A级质量，影响数据质量统计的准确性。Mock数据应该被明确标识，以便在统计和分析时能够过滤。

## 当前Mock数据情况

### RAW层数据
- 共2条Mock记录
- 来源: `https://mock.data/north_port`
- 指标: 北方四港库存、北方四港下海量
- 特征标识:
  - source_url包含"mock.data"
  - original_text包含"[Mock数据]"

### 问题根因
1. 质量评估逻辑(`assess_quality`)未检测Mock数据标识
2. 数据库约束只允许'A','B','C','D'四个等级
3. Mock数据按普通数据评分，被评为B级(76分)

## 修复方案

选择**方案2改进版**: 添加'M'等级（MOCK的缩写）

### 优势
- 单字符，符合现有CHAR(1)字段定义
- 明确标识Mock数据类型
- 统计时易于过滤
- 不影响现有A/B/C/D等级体系

## 修改内容

### 1. 数据库层 (migrations/005_add_mock_quality_grade.sql)
```sql
-- 修改quality_grade约束，添加'M'
ALTER TABLE market_facts_standard 
DROP CONSTRAINT IF EXISTS market_facts_standard_quality_grade_check;

ALTER TABLE market_facts_standard 
ADD CONSTRAINT market_facts_standard_quality_grade_check 
CHECK (quality_grade IN ('A', 'B', 'C', 'D', 'M'));

-- 更新高质量数据视图，排除Mock
CREATE OR REPLACE VIEW market_facts_standard_quality AS
SELECT * FROM market_facts_standard
WHERE is_latest = TRUE 
  AND quality_grade IN ('A', 'B')
  AND quality_grade != 'M';

-- 创建Mock数据视图
CREATE OR REPLACE VIEW market_facts_standard_mock AS
SELECT * FROM market_facts_standard
WHERE is_latest = TRUE 
  AND quality_grade = 'M';
```

### 2. 质量评估逻辑 (backend-rust/src/standardization.rs)
```rust
fn assess_quality(&self, raw_record: &raw_entity::Model) -> QualityAssessment {
    // 首先检查是否是Mock数据
    // 方式1: 检查source_url
    if raw_record.source_url.contains("mock.data") {
        return QualityAssessment {
            grade: "M".to_string(),
            score: 0.0,
            issues: vec!["Mock测试数据".to_string()],
        };
    }
    
    // 方式2: 检查original_text
    if let Some(text) = &raw_record.original_text {
        if text.contains("[Mock数据]") {
            return QualityAssessment {
                grade: "M".to_string(),
                score: 0.0,
                issues: vec!["Mock测试数据".to_string()],
            };
        }
    }
    
    // 非Mock数据，进行正常质量评估
    // ... 现有评估逻辑
}
```

### 3. API模型更新 (backend-rust/src/models.rs)
```rust
pub struct QualityDistribution {
    pub grade_a: u32,
    pub grade_b: u32,
    pub grade_c: u32,
    pub grade_d: u32,
    pub grade_m: u32,  // Mock测试数据
}
```

### 4. 文档更新
- 质量等级注释: `A=优秀 B=良好 C=一般 D=较差 M=Mock测试数据`
- API响应message: `质量分布统计(M=Mock测试数据)`

## 测试结果

### 验证步骤
1. ✅ 数据库约束已更新，支持'M'等级
2. ✅ Mock数据被正确识别并标记为'M'等级
3. ✅ 质量分数为0.00，issues标注"Mock测试数据"
4. ✅ 统计视图自动排除Mock数据

### 测试数据
```
indicator_name | quality_grade | quality_score | source_url
北方四港下海量 | M             | 0.00          | https://mock.data/north_port
北方四港库存   | M             | 0.00          | https://mock.data/north_port
```

### 质量分布统计
```
quality_grade | count
M             | 4
```

## Mock数据检测机制

系统通过以下两种方式识别Mock数据：

1. **source_url检测**: 包含"mock.data"字符串
2. **original_text检测**: 包含"[Mock数据]"标记

满足任一条件即标记为Mock数据(M等级)。

## API影响

### 统计接口自动过滤
- `/api/quality/distribution` - 返回包含grade_m字段
- 高质量数据视图(`market_facts_standard_quality`) - 自动排除M等级
- 可通过`market_facts_standard_mock`视图单独查询Mock数据

### 查询示例
```sql
-- 查询真实数据(排除Mock)
SELECT * FROM market_facts_standard_quality;

-- 查询Mock数据
SELECT * FROM market_facts_standard_mock;

-- 手动过滤
SELECT * FROM market_facts_standard 
WHERE quality_grade != 'M' AND is_latest = true;
```

## 部署步骤

已完成：
1. ✅ 运行数据库迁移 (005_add_mock_quality_grade.sql)
2. ✅ 重新编译Rust后端 (包含Mock检测逻辑)
3. ✅ 重建Docker镜像
4. ✅ 重启backend服务
5. ✅ 验证Mock数据标记正确

## 验收标准

- [x] Mock数据明确标识为'M'等级
- [x] 统计API能过滤Mock数据
- [x] 文档更新(数据库注释、API响应)
- [x] 测试通过(实际Mock数据被正确标记)

## 影响范围

### 修改的文件
1. `migrations/005_add_mock_quality_grade.sql` - 新增
2. `backend-rust/src/standardization.rs` - 质量评估逻辑
3. `backend-rust/src/models.rs` - QualityDistribution模型
4. `backend-rust/src/handlers.rs` - 质量分布API
5. `Dockerfile` - 触发重新构建

### 兼容性
- ✅ 向后兼容: 现有A/B/C/D等级不受影响
- ✅ 数据迁移: 无需迁移历史数据，新标准化时自动应用
- ✅ API兼容: 新增grade_m字段，不影响现有字段

## 后续建议

1. **采集器规范**: 确保所有采集器的Mock数据都使用标准URL格式或标记
2. **监控告警**: 当Mock数据在生产环境出现时发出告警
3. **自动清理**: 定期清理过期的Mock测试数据
4. **文档完善**: 在开发者文档中说明Mock数据的使用和标记规范

## 总结

Mock数据质量标记问题已成功修复。系统现在能够：
- 自动识别Mock数据（通过URL或文本标记）
- 标记为特殊的'M'等级，与真实数据明确区分
- 在统计和查询时自动过滤Mock数据
- 保留独立的Mock数据视图供测试使用

修复耗时约20分钟，符合P3优先级的时间要求。
