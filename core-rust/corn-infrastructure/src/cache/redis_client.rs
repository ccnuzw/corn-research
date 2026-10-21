//! Redis缓存客户端封装
//! 
//! 提供基于Redis的缓存操作，支持JSON序列化和过期时间管理

use redis::{Client, aio::ConnectionManager, AsyncCommands};
use serde::{Serialize, de::DeserializeOwned};
use anyhow::{Result, Context};

/// Redis缓存客户端
#[derive(Clone)]
pub struct RedisCache {
    manager: ConnectionManager,
}

impl RedisCache {
    /// 创建新的Redis缓存客户端
    /// 
    /// # Arguments
    /// * `url` - Redis连接URL (例如: redis://localhost:6379)
    /// 
    /// # Example
    /// ```no_run
    /// let cache = RedisCache::new("redis://localhost:16380").await?;
    /// ```
    pub async fn new(url: &str) -> Result<Self> {
        let client = Client::open(url)
            .context("Failed to create Redis client")?;
        
        let manager = ConnectionManager::new(client)
            .await
            .context("Failed to establish Redis connection")?;
        
        tracing::info!("✅ Redis cache client connected: {}", url);
        
        Ok(Self { manager })
    }
    
    /// 从缓存中获取数据
    /// 
    /// # Arguments
    /// * `key` - 缓存键
    /// 
    /// # Returns
    /// * `Some(T)` - 缓存命中，返回反序列化后的数据
    /// * `None` - 缓存未命中或反序列化失败
    pub async fn get<T: DeserializeOwned>(&self, key: &str) -> Option<T> {
        let mut conn = self.manager.clone();
        
        match conn.get::<_, String>(key).await {
            Ok(json_str) => {
                match serde_json::from_str::<T>(&json_str) {
                    Ok(data) => {
                        tracing::debug!("✅ Cache hit: {}", key);
                        Some(data)
                    }
                    Err(e) => {
                        tracing::warn!("⚠️ Cache deserialization failed for key {}: {}", key, e);
                        None
                    }
                }
            }
            Err(e) => {
                tracing::debug!("Cache miss: {} ({})", key, e);
                None
            }
        }
    }
    
    /// 设置缓存数据，带过期时间
    /// 
    /// # Arguments
    /// * `key` - 缓存键
    /// * `value` - 要缓存的数据（会被序列化为JSON）
    /// * `seconds` - 过期时间（秒）
    /// 
    /// # Example
    /// ```no_run
    /// cache.set_ex("latest:corn:30", &data, 300).await?;
    /// ```
    pub async fn set_ex<T: Serialize>(&self, key: &str, value: &T, seconds: u64) -> Result<()> {
        let mut conn = self.manager.clone();
        
        let json_str = serde_json::to_string(value)
            .context("Failed to serialize value to JSON")?;
        
        conn.set_ex::<_, _, ()>(key, json_str, seconds)
            .await
            .context("Failed to set cache value")?;
        
        tracing::debug!("✅ Cache set: {} (TTL: {}s)", key, seconds);
        
        Ok(())
    }
    
    /// 删除缓存键
    /// 
    /// # Arguments
    /// * `key` - 要删除的缓存键
    pub async fn delete(&self, key: &str) -> Result<()> {
        let mut conn = self.manager.clone();
        
        conn.del::<_, ()>(key)
            .await
            .context("Failed to delete cache key")?;
        
        tracing::debug!("🗑️ Cache deleted: {}", key);
        
        Ok(())
    }
    
    /// 检查键是否存在
    /// 
    /// # Arguments
    /// * `key` - 要检查的缓存键
    pub async fn exists(&self, key: &str) -> Result<bool> {
        let mut conn = self.manager.clone();
        
        let exists: bool = conn.exists(key)
            .await
            .context("Failed to check key existence")?;
        
        Ok(exists)
    }
    
    /// 批量删除匹配模式的键
    /// 
    /// # Arguments
    /// * `pattern` - 键匹配模式（例如: "latest:*"）
    /// 
    /// # Note
    /// 生产环境慎用SCAN命令，大量键时可能影响性能
    pub async fn delete_pattern(&self, pattern: &str) -> Result<usize> {
        let mut conn = self.manager.clone();
        
        // 使用SCAN命令遍历键（避免KEYS命令阻塞）
        let mut cursor: u64 = 0;
        let mut deleted_count = 0;
        
        loop {
            let (new_cursor, keys): (u64, Vec<String>) = redis::cmd("SCAN")
                .arg(cursor)
                .arg("MATCH")
                .arg(pattern)
                .arg("COUNT")
                .arg(100)
                .query_async(&mut conn)
                .await
                .context("Failed to scan keys")?;
            
            if !keys.is_empty() {
                let count: usize = conn.del(&keys)
                    .await
                    .context("Failed to delete keys")?;
                deleted_count += count;
            }
            
            cursor = new_cursor;
            if cursor == 0 {
                break;
            }
        }
        
        tracing::info!("🗑️ Deleted {} keys matching pattern: {}", deleted_count, pattern);
        
        Ok(deleted_count)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde::{Deserialize, Serialize};
    
    #[derive(Debug, Serialize, Deserialize, PartialEq)]
    struct TestData {
        id: u32,
        name: String,
    }
    
    #[tokio::test]
    #[ignore] // 需要Redis实例才能运行
    async fn test_redis_cache_operations() -> Result<()> {
        let cache = RedisCache::new("redis://localhost:16380").await?;
        let key = "test:data:1";
        
        let test_data = TestData {
            id: 1,
            name: "Test".to_string(),
        };
        
        // 测试set_ex
        cache.set_ex(key, &test_data, 60).await?;
        
        // 测试exists
        assert!(cache.exists(key).await?);
        
        // 测试get
        let retrieved: Option<TestData> = cache.get(key).await;
        assert_eq!(retrieved, Some(test_data));
        
        // 测试delete
        cache.delete(key).await?;
        assert!(!cache.exists(key).await?);
        
        Ok(())
    }
}
