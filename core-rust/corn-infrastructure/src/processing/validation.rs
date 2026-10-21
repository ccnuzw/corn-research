//! 数据验证服务
//! 
//! 业务规则验证和数据质量检查

use super::dedup::RawRecord;

/// 验证错误
#[derive(Debug)]
pub enum ValidationError {
    InvalidValue(String),
    InvalidDate(String),
    MissingField(String),
    OutOfRange(String),
}

/// 验证结果
#[derive(Debug)]
pub struct ValidationResult {
    pub valid: Vec<RawRecord>,
    pub invalid: Vec<(RawRecord, ValidationError)>,
}

/// 验证服务
pub struct ValidationService;

impl ValidationService {
    /// 验证记录
    pub fn validate(records: Vec<RawRecord>) -> ValidationResult {
        let mut valid = Vec::new();
        let mut invalid = Vec::new();
        
        for record in records {
            match Self::validate_record(&record) {
                Ok(_) => valid.push(record),
                Err(e) => invalid.push((record, e)),
            }
        }
        
        ValidationResult { valid, invalid }
    }
    
    /// 验证单条记录
    fn validate_record(record: &RawRecord) -> Result<(), ValidationError> {
        // 验证数值范围
        if record.value < 0.0 {
            return Err(ValidationError::InvalidValue(
                "Value cannot be negative".to_string()
            ));
        }
        
        if record.value > 100_000.0 {
            return Err(ValidationError::OutOfRange(
                "Value too large".to_string()
            ));
        }
        
        // 验证必填字段
        if record.business_date.is_empty() {
            return Err(ValidationError::MissingField(
                "business_date is required".to_string()
            ));
        }
        
        if record.indicator.is_empty() {
            return Err(ValidationError::MissingField(
                "indicator is required".to_string()
            ));
        }
        
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validation() {
        let records = vec![
            RawRecord {
                business_date: "2026-10-20".to_string(),
                indicator: "山东到车".to_string(),
                value: 1040.0,
                region: "山东".to_string(),
                source_url: "http://example.com/1".to_string(),
            },
            RawRecord {
                business_date: "".to_string(), // 无效：日期为空
                indicator: "山东到车".to_string(),
                value: 1050.0,
                region: "山东".to_string(),
                source_url: "http://example.com/2".to_string(),
            },
            RawRecord {
                business_date: "2026-10-21".to_string(),
                indicator: "山东到车".to_string(),
                value: -100.0, // 无效：负数
                region: "山东".to_string(),
                source_url: "http://example.com/3".to_string(),
            },
        ];
        
        let result = ValidationService::validate(records);
        assert_eq!(result.valid.len(), 1);
        assert_eq!(result.invalid.len(), 2);
    }
}
