use sqlx::{PgPool, postgres::PgPoolOptions, Row};
use uuid::Uuid;
use chrono::Utc;

use crate::raw_record::RawRecord;
use crate::cache::RedisCache;

pub struct PostgresRepository {
    pool: PgPool,
    cache: Option<RedisCache>,
}

impl PostgresRepository {
    /// 创建新的PostgreSQL连接池（不带缓存）
    pub async fn new(database_url: &str) -> Result<Self, sqlx::Error> {
        let pool = PgPoolOptions::new()
            .max_connections(5)
            .connect(database_url)
            .await?;
        
        Ok(Self { pool, cache: None })
    }
    
    /// 创建新的PostgreSQL连接池（带Redis缓存）
    pub async fn new_with_cache(
        database_url: &str,
        redis_url: &str,
    ) -> Result<Self, sqlx::Error> {
        let pool = PgPoolOptions::new()
            .max_connections(5)
            .connect(database_url)
            .await?;
        
        // 尝试连接Redis，失败时仍可降级使用（不带缓存）
        let cache = match RedisCache::new(redis_url).await {
            Ok(cache) => {
                tracing::info!("✅ Repository initialized with Redis cache");
                Some(cache)
            }
            Err(e) => {
                tracing::warn!("⚠️ Redis connection failed, running without cache: {}", e);
                None
            }
        };
        
        Ok(Self { pool, cache })
    }
    
    /// 保存原始采集记录到RAW层
    pub async fn save_raw_records(
        &self,
        records: &[RawRecord],
    ) -> Result<usize, sqlx::Error> {
        let mut tx = self.pool.begin().await?;
        let mut saved = 0;
        
        for record in records {
            let id = Uuid::new_v4();
            
            // 生成去重键
            let dedup_key = format!(
                "{}_{}_{}",
                record.collector_id,
                record.business_date,
                record.indicator_name
            );
            
            // 插入记录（冲突则忽略）
            let result = sqlx::query(
                r#"
                INSERT INTO raw_collection_records (
                    id, collector_id, business_date,
                    indicator_name, value, unit, region,
                    source_url, original_text,
                    dedup_key, collected_at, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (dedup_key) DO NOTHING
                "#
            )
            .bind(id)
            .bind(&record.collector_id)
            .bind(&record.business_date)
            .bind(&record.indicator_name)
            .bind(record.value)
            .bind(&record.unit)
            .bind(&record.region)
            .bind(&record.source_url)
            .bind(&record.original_text)
            .bind(&dedup_key)
            .bind(Utc::now())
            .bind(Utc::now())
            .execute(&mut *tx)
            .await?;
            
            if result.rows_affected() > 0 {
                saved += 1;
            }
        }
        
        tx.commit().await?;
        Ok(saved)
    }
    
    /// 查询最新数据
    pub async fn get_latest_records(
        &self,
        indicator: &str,
        days: i32,
    ) -> Result<Vec<RawRecord>, sqlx::Error> {
        let rows = sqlx::query(
            r#"
            SELECT 
                collector_id, business_date, indicator_name,
                value, unit, region, source_url, original_text,
                collected_at
            FROM raw_collection_records
            WHERE indicator_name = $1
              AND business_date >= CURRENT_DATE - $2
            ORDER BY business_date DESC, collected_at DESC
            LIMIT 100
            "#
        )
        .bind(indicator)
        .bind(days)
        .fetch_all(&self.pool)
        .await?;
        
        let records: Vec<RawRecord> = rows
            .into_iter()
            .map(|row| RawRecord {
                collector_id: row.get("collector_id"),
                business_date: row.get("business_date"),
                indicator_name: row.get("indicator_name"),
                value: row.get::<f64, _>("value"),
                unit: row.get("unit"),
                region: row.get("region"),
                source_url: row.get("source_url"),
                original_text: row.get("original_text"),
                collected_at: row.get::<chrono::DateTime<Utc>, _>("collected_at")
                    .to_rfc3339(),
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
    /// * `indicator` - 指标名称（如："corn"）
    /// * `days` - 查询最近N天的数据
    pub async fn get_latest_records_cached(
        &self,
        indicator: &str,
        days: i32,
    ) -> Result<Vec<RawRecord>, sqlx::Error> {
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
    pub async fn get_stats(&self) -> Result<RepositoryStats, sqlx::Error> {
        let row = sqlx::query(
            r#"
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT indicator_name) as total_indicators,
                COUNT(DISTINCT collector_id) as total_collectors,
                MAX(collected_at) as latest_collection
            FROM raw_collection_records
            "#
        )
        .fetch_one(&self.pool)
        .await?;
        
        Ok(RepositoryStats {
            total_records: row.get::<i64, _>("total_records") as usize,
            total_indicators: row.get::<i64, _>("total_indicators") as usize,
            total_collectors: row.get::<i64, _>("total_collectors") as usize,
            latest_collection: row.get("latest_collection"),
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
