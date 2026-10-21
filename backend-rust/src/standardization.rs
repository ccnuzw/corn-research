//! Data Standardization Service
//! RAW层 → STANDARD层 数据转换

use sea_orm::*;
use sea_orm::prelude::*;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc, NaiveDate};
use rust_decimal::Decimal;
use uuid::Uuid;

use crate::db::entities as raw_entity;

/// STANDARD层实体
#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
#[sea_orm(table_name = "market_facts_standard")]
pub struct Model {
    #[sea_orm(primary_key, auto_increment = false)]
    pub id: Uuid,
    pub business_date: Date,
    pub indicator_name: String,
    pub value: Decimal,
    pub unit: String,
    pub region: Option<String>,
    
    // 质量评分
    pub quality_grade: String,  // A/B/C/D
    pub quality_score: Option<Decimal>,
    pub quality_issues: Option<Json>,
    
    // 数据血统
    pub source_id: String,
    pub raw_record_id: Option<Uuid>,
    
    // 时间戳
    pub collected_at: DateTimeWithTimeZone,
    pub standardized_at: DateTimeWithTimeZone,
    
    // 版本管理
    pub version: i32,
    pub is_latest: bool,
    
    pub metadata: Option<Json>,
    pub created_at: Option<DateTimeWithTimeZone>,
    pub updated_at: Option<DateTimeWithTimeZone>,
}

#[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
pub enum Relation {}

impl ActiveModelBehavior for ActiveModel {}

/// 数据标准化服务
pub struct StandardizationService {
    db: DatabaseConnection,
}

/// 质量评估结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualityAssessment {
    pub grade: String,      // A/B/C/D
    pub score: f32,         // 0-100
    pub issues: Vec<String>,
}

impl StandardizationService {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }
    
    /// RAW → STANDARD 自动转换
    pub async fn standardize_raw_record(
        &self,
        raw_record: &raw_entity::Model,
    ) -> Result<Model, DbErr> {
        
        // 1. 数据清洗
        let cleaned_value = self.clean_value(raw_record.value)?;
        let cleaned_indicator = self.clean_indicator_name(&raw_record.indicator_name);
        
        // 2. 质量评估
        let quality = self.assess_quality(raw_record);
        
        // 3. 检查是否已存在（去重）
        let existing = self.find_existing(
            &raw_record.business_date,
            &cleaned_indicator,
            &raw_record.collector_id,
        ).await?;
        
        // 4. 确定版本号
        let version = if let Some(existing_record) = existing {
            // 标记旧版本为非最新
            self.mark_old_version_obsolete(existing_record.id).await?;
            existing_record.version + 1
        } else {
            1
        };
        
        // 5. 创建STANDARD记录
        let standard_record = Model {
            id: Uuid::new_v4(),
            business_date: raw_record.business_date,
            indicator_name: cleaned_indicator,
            value: cleaned_value,
            unit: raw_record.unit.clone(),
            region: raw_record.region.clone(),
            
            quality_grade: quality.grade.clone(),
            quality_score: Some(Decimal::try_from(quality.score).unwrap_or_default()),
            quality_issues: Some(serde_json::to_value(&quality.issues).unwrap().into()),
            
            source_id: raw_record.collector_id.clone(),
            raw_record_id: Some(raw_record.id),
            
            collected_at: raw_record.collected_at,
            standardized_at: DateTimeWithTimeZone::from(Utc::now()),
            
            version,
            is_latest: true,
            
            metadata: None,
            created_at: Some(DateTimeWithTimeZone::from(Utc::now())),
            updated_at: Some(DateTimeWithTimeZone::from(Utc::now())),
        };
        
        // 6. 保存到数据库
        let active_model: ActiveModel = standard_record.clone().into();
        Entity::insert(active_model)
            .exec(&self.db)
            .await?;
        
        Ok(standard_record)
    }
    
    /// 批量转换
    pub async fn standardize_batch(
        &self,
        raw_records: Vec<raw_entity::Model>,
    ) -> Result<Vec<Model>, DbErr> {
        let mut results = Vec::new();
        
        for raw_record in raw_records {
            match self.standardize_raw_record(&raw_record).await {
                Ok(standard_record) => {
                    tracing::info!(
                        "✓ Standardized: {} {} = {}",
                        standard_record.business_date,
                        standard_record.indicator_name,
                        standard_record.value
                    );
                    results.push(standard_record);
                }
                Err(e) => {
                    tracing::error!(
                        "✗ Failed to standardize record {}: {}",
                        raw_record.id,
                        e
                    );
                }
            }
        }
        
        Ok(results)
    }
    
    /// 自动晋升：将B级以上的RAW数据自动转换到STANDARD
    pub async fn auto_promote_quality_data(&self) -> Result<usize, DbErr> {
        // 查找未被标准化的RAW记录（通过LEFT JOIN检查）
        let raw_records = raw_entity::Entity::find()
            .filter(raw_entity::Column::CreatedAt.gte(Utc::now() - chrono::Duration::hours(24)))
            .all(&self.db)
            .await?;
        
        let mut promoted_count = 0;
        
        for raw_record in raw_records {
            // 评估质量
            let quality = self.assess_quality(&raw_record);
            
            // 只晋升B级以上
            if quality.grade == "A" || quality.grade == "B" {
                // 检查是否已经标准化
                let already_standardized = Entity::find()
                    .filter(Column::RawRecordId.eq(raw_record.id))
                    .one(&self.db)
                    .await?;
                
                if already_standardized.is_none() {
                    match self.standardize_raw_record(&raw_record).await {
                        Ok(_) => {
                            promoted_count += 1;
                            tracing::info!(
                                "✓ Auto-promoted: {} (Grade: {})",
                                raw_record.indicator_name,
                                quality.grade
                            );
                        }
                        Err(e) => {
                            tracing::warn!(
                                "✗ Failed to auto-promote {}: {}",
                                raw_record.id,
                                e
                            );
                        }
                    }
                }
            }
        }
        
        Ok(promoted_count)
    }
    
    // ===== 内部辅助方法 =====
    
    /// 数据清洗：数值
    fn clean_value(&self, value: Decimal) -> Result<Decimal, DbErr> {
        // 检查合理范围
        if value < Decimal::new(0, 0) {
            return Err(DbErr::Custom("Negative value not allowed".to_string()));
        }
        
        // 四舍五入到4位小数
        Ok(value.round_dp(4))
    }
    
    /// 数据清洗：指标名称
    fn clean_indicator_name(&self, name: &str) -> String {
        name.trim().to_string()
    }
    
    /// 质量评估
    fn assess_quality(&self, raw_record: &raw_entity::Model) -> QualityAssessment {
        let mut score = 100.0;
        let mut issues = Vec::new();
        
        // 评估1: 数据来源可信度
        let source_score = match raw_record.collector_id.as_str() {
            id if id.contains("official") => 100.0,      // 官方来源 = A
            id if id.contains("exchange") => 95.0,       // 交易所 = A
            id if id.contains("commercial") => 85.0,     // 商业数据 = B
            id if id.contains("public") => 75.0,         // 公开媒体 = B-C
            _ => 60.0,                                    // 其他 = C
        };
        score = score * 0.4 + source_score * 0.6;  // 来源权重60%
        
        // 评估2: 数据完整性
        if raw_record.original_text.is_none() {
            score -= 5.0;
            issues.push("缺少原文摘录".to_string());
        }
        
        if raw_record.region.is_none() {
            score -= 3.0;
            issues.push("缺少地区信息".to_string());
        }
        
        // 评估3: 数据合理性（基于业务规则）
        let value_f64 = raw_record.value.to_string().parse::<f64>().unwrap_or(0.0);
        
        if raw_record.indicator_name.contains("到车") {
            // 山东到车量合理范围：100-2000台
            if value_f64 < 100.0 || value_f64 > 2000.0 {
                score -= 15.0;
                issues.push("数值超出合理范围".to_string());
            }
        } else if raw_record.indicator_name.contains("库存") {
            // 北方四港库存合理范围：100-300万吨
            if value_f64 < 100.0 || value_f64 > 300.0 {
                score -= 15.0;
                issues.push("数值超出合理范围".to_string());
            }
        }
        
        // 评估4: 时效性
        let now = Utc::now();
        let collected_time: DateTime<Utc> = raw_record.collected_at.into();
        let age_hours = (now - collected_time).num_hours();
        
        if age_hours > 72 {  // 超过3天
            score -= 10.0;
            issues.push("数据时效性较差".to_string());
        }
        
        // 确定等级
        let grade = if score >= 90.0 {
            "A"
        } else if score >= 75.0 {
            "B"
        } else if score >= 60.0 {
            "C"
        } else {
            "D"
        };
        
        QualityAssessment {
            grade: grade.to_string(),
            score,
            issues,
        }
    }
    
    /// 查找已存在的记录
    async fn find_existing(
        &self,
        business_date: &Date,
        indicator_name: &str,
        source_id: &str,
    ) -> Result<Option<Model>, DbErr> {
        Entity::find()
            .filter(Column::BusinessDate.eq(*business_date))
            .filter(Column::IndicatorName.eq(indicator_name))
            .filter(Column::SourceId.eq(source_id))
            .filter(Column::IsLatest.eq(true))
            .one(&self.db)
            .await
    }
    
    /// 标记旧版本为非最新
    async fn mark_old_version_obsolete(&self, id: Uuid) -> Result<(), DbErr> {
        let mut model: ActiveModel = Entity::find_by_id(id)
            .one(&self.db)
            .await?
            .ok_or(DbErr::RecordNotFound("Record not found".to_string()))?
            .into();
        
        model.is_latest = Set(false);
        model.update(&self.db).await?;
        
        Ok(())
    }
}

// 为了能在其他模块中使用
pub use Entity as StandardEntity;
