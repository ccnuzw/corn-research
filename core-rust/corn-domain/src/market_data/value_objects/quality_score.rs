//! 质量分数值对象

use thiserror::Error;

#[derive(Error, Debug)]
pub enum QualityScoreError {
    #[error("Quality score must be between 0 and 1, got {0}")]
    InvalidScore(f64),
}

/// 质量分数值对象（不可变）
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct QualityScore {
    value: f64,
}

impl QualityScore {
    /// 创建新的质量分数
    pub fn new(value: f64) -> Result<Self, QualityScoreError> {
        if !(0.0..=1.0).contains(&value) {
            return Err(QualityScoreError::InvalidScore(value));
        }
        Ok(Self { value })
    }
    
    /// 从因子计算
    pub fn from_factors(
        source_tier: f64,
        completeness: f64,
        timeliness: f64,
    ) -> Result<Self, QualityScoreError> {
        let score = source_tier * completeness * timeliness;
        Self::new(score)
    }
    
    /// 获取值
    pub fn value(&self) -> f64 {
        self.value
    }
    
    /// 是否高质量（>= 0.8）
    pub fn is_high_quality(&self) -> bool {
        self.value >= 0.8
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_quality_score() {
        let score = QualityScore::new(0.9).unwrap();
        assert_eq!(score.value(), 0.9);
        assert!(score.is_high_quality());
    }

    #[test]
    fn test_invalid_score() {
        assert!(QualityScore::new(1.5).is_err());
        assert!(QualityScore::new(-0.1).is_err());
    }
}
