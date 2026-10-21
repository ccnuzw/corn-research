//! 价格实体

use chrono::NaiveDate;
use rust_decimal::Decimal;
use crate::market_data::value_objects::{Location, QualityScore};

/// 价格实体
#[derive(Debug, Clone)]
pub struct Price {
    /// 业务日期
    pub date: NaiveDate,
    
    /// 商品
    pub commodity: String,
    
    /// 地区
    pub location: Location,
    
    /// 价格
    pub value: Decimal,
    
    /// 单位
    pub unit: String,
    
    /// 质量分数
    pub quality_score: QualityScore,
    
    /// 来源URL
    pub source_url: String,
}

impl Price {
    /// 创建新价格
    pub fn new(
        date: NaiveDate,
        commodity: String,
        location: Location,
        value: Decimal,
        unit: String,
        quality_score: QualityScore,
        source_url: String,
    ) -> Self {
        Self {
            date,
            commodity,
            location,
            value,
            unit,
            quality_score,
            source_url,
        }
    }
    
    /// 是否高质量
    pub fn is_high_quality(&self) -> bool {
        self.quality_score.is_high_quality()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rust_decimal_macros::dec;

    #[test]
    fn test_price_creation() {
        let price = Price::new(
            NaiveDate::from_ymd_opt(2026, 10, 20).unwrap(),
            "corn".to_string(),
            Location::new("山东".to_string()),
            dec!(2800.0),
            "元/吨".to_string(),
            QualityScore::new(0.9).unwrap(),
            "https://example.com".to_string(),
        );
        
        assert_eq!(price.commodity, "corn");
        assert!(price.is_high_quality());
    }
}
