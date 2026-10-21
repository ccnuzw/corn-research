//! PostgreSQL Repository - SeaORM实现
//!
//! 使用SeaORM操作数据库

use sea_orm::{
    Database, DatabaseConnection, EntityTrait, QueryFilter, QueryOrder,
    ColumnTrait, Set, ActiveModelTrait, DbErr, QuerySelect, PaginatorTrait, ConnectionTrait,
};
use chrono::Utc;
use uuid::Uuid;

use crate::python_bridge::RawRecord;
use crate::cache::RedisCache;
use crate::entities::{raw_collection_records, prelude::RawCollectionRecords};

pub struct PostgresRepositorySeaOrm {
    db: DatabaseConnection,
    cache: Option<RedisCache>,
}

impl PostgresRepositorySeaOrm {
    /// 创建新的PostgreSQL连接（不带缓存）
    pub async fn new(database_url: &str) -> Result<Self, DbErr> {
        let db = Database::connect(database_url).await?;
        
        tracing::info!("✅ PostgreSQL connected (SeaORM)");
        
        Ok(Self { db, cache: None })
    }
    
    /// 创建新的PostgreSQL连接（带Redis缓存）
    pub async fn new_with_cache(
        database_url: &str,
        redis_url: &str,
    ) -> Result<Self, DbErr> {
        let db = Database::connect(database_url).await?;
        
        // 尝试连接Redis，失败时仍可降级使用（不带缓存）
        let cache = match RedisCache::new(redis_url).await {
            Ok(cache) => {
                tracing::info!("✅ Repository initialized with Redis cache (SeaORM)");
                Some(cache)
            }
            Err(e) => {
                tracing::warn!("⚠️ Redis connection failed, running without cache: {}", e);
                None
            }
        };
        
        Ok(Self { db, cache })
    }
    
    /// 保存原始采集记录到RAW层
    pub async fn save_raw_records(
        &self,
        records: &[RawRecord],
    ) -> Result<usize, DbErr> {
        let mut saved = 0;
        
        for record in records {
            // 生成去重键
            let dedup_key = format!(
                "{}_{}_{}_{}",
                record.collector_id,
                record.business_date,
                record.indicator_name,
                record.region.as_deref().unwrap_or("global")
            );
            
            // 检查是否已存在
            let existing = RawCollectionRecords::find()
                .filter(raw_collection_records::Column::DedupKey.eq(&dedup_key))
                .one(&self.db)
                .await?;
            
            if existing.is_some() {
                tracing::debug!("⏭️ Record already exists: {}", dedup_key);
                continue;
            }
            
            // 解析业务日期
            let business_date = chrono::NaiveDate::parse_from_str(
                &record.business_date,
                "%Y-%m-%d"
            ).map_err(|e| DbErr::Custom(format!("Invalid date format: {}", e)))?;
            
            // 解析采集时间
            let collected_at = chrono::DateTime::parse_from_rfc3339(&record.collected_at)
                .map_err(|e| DbErr::Custom(format!("Invalid datetime format: {}", e)))?
                .with_timezone(&Utc);
            
            // 转换value为Decimal
            let value_decimal = rust_decimal::Decimal::from_f64_retain(record.value)
                .ok_or_else(|| DbErr::Custom(format!("Invalid decimal value: {}", record.value)))?;
            
            // 创建ActiveModel
            let active_model = raw_collection_records::ActiveModel {
                id: Set(Uuid::new_v4()),
                collector_id: Set(record.collector_id.clone()),
                business_date: Set(business_date),
                indicator_name: Set(record.indicator_name.clone()),
                value: Set(value_decimal),
                unit: Set(record.unit.clone()),
                region: Set(record.region.clone()),
                source_url: Set(record.source_url.clone()),
                original_text: Set(record.original_text.clone()),
                dedup_key: Set(dedup_key),
                collected_at: Set(collected_at.into()),
                created_at: Set(Some(Utc::now().into())),
                updated_at: Set(Some(Utc::now().into())),
            };
            
            // 插入记录
            active_model.insert(&self.db).await?;
            saved += 1;
        }
        
        tracing::info!("💾 Saved {} new records to database", saved);
        
        Ok(saved)
    }
    
    /// 查询最新数据
    pub async fn get_latest_records(
        &self,
        indicator: &str,
        days: i32,
    ) -> Result<Vec<RawRecord>, DbErr> {
        let cutoff_date = chrono::Utc::now().date_naive() - chrono::Days::new(days as u64);
        
        let models = RawCollectionRecords::find()
            .filter(raw_collection_records::Column::IndicatorName.eq(indicator))
            .filter(raw_collection_records::Column::BusinessDate.gte(cutoff_date))
            .order_by_desc(raw_collection_records::Column::BusinessDate)
            .order_by_desc(raw_collection_records::Column::CollectedAt)
            .limit(100)
            .all(&self.db)
            .await?;
        
        let records: Vec<RawRecord> = models
            .into_iter()
            .map(|m| RawRecord {
                collector_id: m.collector_id,
                business_date: m.business_date.to_string(),
                indicator_name: m.indicator_name,
                value: m.value.to_string().parse::<f64>().unwrap_or(0.0),
                unit: m.unit,
                region: m.region,
                source_url: m.source_url,
                original_text: m.original_text,
                collected_at: m.collected_at.to_rfc3339(),
            })
            .collect();
        
        Ok(records)
    }
    
    /// 查询最新数据（带缓存）
    /// 
    /// # 缓存策略
    /// - 缓存键格式：latest:{indicator}:{days}
    /// - TTL：300秒（5分钟）
    /// - 缓存未命中或失败时降级到数据库查询
    /// 
    /// # Arguments
    /// * `indicator` - 指标名称（如：\"corn\"）
    /// * `days` - 查询最近N天的数据
    pub async fn get_latest_records_cached(
        &self,
        indicator: &str,
        days: i32,
    ) -> Result<Vec<RawRecord>, DbErr> {
        // 如果没有配置缓存，直接查数据库
        let Some(cache) = &self.cache else {
            return self.get_latest_records(indicator, days).await;
        };
        
        // 生成缓存键
        let cache_key = format!("latest:{}:{}", indicator, days);
        
        // 尝试从缓存获取
        if let Some(cached_records) = cache.get::<Vec<RawRecord>>(&cache_key).await {
            tracing::info!("🚀 Cache hit for {}, returning {} records", cache_key, cached_records.len());
            return Ok(cached_records);
        }
        
        // 缓存未命中，查询数据库
        tracing::info!("💾 Cache miss for {}, querying database...", cache_key);
        let start = std::time::Instant::now();
        
        let records = self.get_latest_records(indicator, days).await?;
        
        let query_time = start.elapsed();
        tracing::info!("📊 Database query completed in {:?}, {} records", query_time, records.len());
        
        // 写入缓存（忽略错误，不影响主流程）
        if let Err(e) = cache.set_ex(&cache_key, &records, 300).await {
            tracing::warn!("⚠️ Failed to cache results for {}: {}", cache_key, e);
        }
        
        Ok(records)
    }
    
    /// 获取统计信息
    pub async fn get_stats(&self) -> Result<RepositoryStats, DbErr> {
        use sea_orm::sea_query::{Expr, Func};
        
        // 总记录数
        let total_records = RawCollectionRecords::find()
            .count(&self.db)
            .await? as usize;
        
        // 获取唯一指标数和采集器数（需要原生SQL）
        let query_result = self.db.query_one(sea_orm::Statement::from_string(
            sea_orm::DatabaseBackend::Postgres,
            r#"
            SELECT 
                COUNT(DISTINCT indicator_name) as total_indicators,
                COUNT(DISTINCT collector_id) as total_collectors,
                MAX(collected_at) as latest_collection
            FROM raw_collection_records
            "#.to_owned()
        )).await?;
        
        let (total_indicators, total_collectors, latest_collection) = if let Some(row) = query_result {
            (
                row.try_get::<i64>("", "total_indicators").unwrap_or(0) as usize,
                row.try_get::<i64>("", "total_collectors").unwrap_or(0) as usize,
                row.try_get::<chrono::DateTime<Utc>>("", "latest_collection").ok(),
            )
        } else {
            (0, 0, None)
        };
        
        Ok(RepositoryStats {
            total_records,
            total_indicators,
            total_collectors,
            latest_collection,
        })
    }
}

#[derive(Debug)]
pub struct RepositoryStats {
    pub total_records: usize,
    pub total_indicators: usize,
    pub total_collectors: usize,
    pub latest_collection: Option<chrono::DateTime<Utc>>,
}
