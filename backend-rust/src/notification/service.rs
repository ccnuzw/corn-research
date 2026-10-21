//! Notification Service - 消息通知服务
//!
//! 提供实时消息通知功能（Redis Pub/Sub + WebSocket）

use redis::{Client, aio::ConnectionManager, AsyncCommands};
use serde::{Serialize, Deserialize};
use chrono::Utc;
use uuid::Uuid;
use anyhow::{Result, Context};

/// 通知级别
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum NotificationLevel {
    Info,
    Success,
    Warning,
    Error,
}

/// 通知消息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Notification {
    pub id: String,
    pub level: NotificationLevel,
    pub title: String,
    pub message: String,
    pub timestamp: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<serde_json::Value>,
}

impl Notification {
    pub fn new(level: NotificationLevel, title: String, message: String) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            level,
            title,
            message,
            timestamp: Utc::now().to_rfc3339(),
            metadata: None,
        }
    }
    
    pub fn with_metadata(mut self, metadata: serde_json::Value) -> Self {
        self.metadata = Some(metadata);
        self
    }
    
    /// 创建采集开始通知
    pub fn collection_started(collector_id: &str) -> Self {
        Self::new(
            NotificationLevel::Info,
            "采集开始".to_string(),
            format!("采集器 {} 开始运行", collector_id),
        ).with_metadata(serde_json::json!({
            "collector_id": collector_id,
            "event": "collection_started"
        }))
    }
    
    /// 创建采集完成通知
    pub fn collection_completed(collector_id: &str, record_count: usize) -> Self {
        Self::new(
            NotificationLevel::Success,
            "采集完成".to_string(),
            format!("采集器 {} 完成，共采集 {} 条数据", collector_id, record_count),
        ).with_metadata(serde_json::json!({
            "collector_id": collector_id,
            "record_count": record_count,
            "event": "collection_completed"
        }))
    }
    
    /// 创建采集失败通知
    pub fn collection_failed(collector_id: &str, error: &str) -> Self {
        Self::new(
            NotificationLevel::Error,
            "采集失败".to_string(),
            format!("采集器 {} 失败: {}", collector_id, error),
        ).with_metadata(serde_json::json!({
            "collector_id": collector_id,
            "error": error,
            "event": "collection_failed"
        }))
    }
    
    /// 创建数据异常通知
    pub fn data_anomaly(indicator: &str, details: &str) -> Self {
        Self::new(
            NotificationLevel::Warning,
            "数据异常".to_string(),
            format!("指标 {} 检测到异常: {}", indicator, details),
        ).with_metadata(serde_json::json!({
            "indicator": indicator,
            "details": details,
            "event": "data_anomaly"
        }))
    }
}

/// 通知服务
#[derive(Clone)]
pub struct NotificationService {
    redis: ConnectionManager,
    channel: String,
}

impl NotificationService {
    /// 创建新的通知服务
    pub async fn new(redis_url: &str) -> Result<Self> {
        let client = Client::open(redis_url)
            .context("Failed to create Redis client")?;
        
        let redis = ConnectionManager::new(client)
            .await
            .context("Failed to establish Redis connection")?;
        
        tracing::info!("✅ Notification service connected to Redis");
        
        Ok(Self {
            redis,
            channel: "corn:notifications".to_string(),
        })
    }
    
    /// 发布通知
    pub async fn publish(&self, notification: Notification) -> Result<()> {
        let mut conn = self.redis.clone();
        
        let json = serde_json::to_string(&notification)
            .context("Failed to serialize notification")?;
        
        conn.publish::<_, _, ()>(&self.channel, json)
            .await
            .context("Failed to publish notification")?;
        
        tracing::info!("📢 Published notification: {} - {}", notification.level_emoji(), notification.title);
        
        // 同时存储到历史记录（最多保留100条）
        self.store_to_history(&notification).await?;
        
        Ok(())
    }
    
    /// 存储通知到历史记录
    async fn store_to_history(&self, notification: &Notification) -> Result<()> {
        let mut conn = self.redis.clone();
        let key = "corn:notifications:history";
        
        let json = serde_json::to_string(notification)
            .context("Failed to serialize notification for history")?;
        
        // 使用LPUSH添加到列表头部
        conn.lpush::<_, _, ()>(key, json)
            .await
            .context("Failed to store notification to history")?;
        
        // 保持列表长度在100以内
        conn.ltrim::<_, ()>(key, 0, 99)
            .await
            .context("Failed to trim notification history")?;
        
        Ok(())
    }
    
    /// 获取历史通知
    pub async fn get_history(&self, limit: usize) -> Result<Vec<Notification>> {
        let mut conn = self.redis.clone();
        let key = "corn:notifications:history";
        
        let items: Vec<String> = conn.lrange(key, 0, (limit - 1) as isize)
            .await
            .context("Failed to get notification history")?;
        
        let notifications: Vec<Notification> = items
            .into_iter()
            .filter_map(|json| serde_json::from_str(&json).ok())
            .collect();
        
        Ok(notifications)
    }
    
    /// 标记通知为已读（实现待定）
    pub async fn mark_as_read(&self, notification_id: &str) -> Result<()> {
        // 可以使用Redis Set存储已读通知ID
        let mut conn = self.redis.clone();
        let key = "corn:notifications:read";
        
        conn.sadd::<_, _, ()>(key, notification_id)
            .await
            .context("Failed to mark notification as read")?;
        
        tracing::debug!("✅ Notification {} marked as read", notification_id);
        
        Ok(())
    }
    
    /// 快捷方法：发送通知
    pub async fn notify(&self, title: &str, message: &str, level: &str) -> Result<()> {
        let level = match level {
            "info" => NotificationLevel::Info,
            "success" => NotificationLevel::Success,
            "warning" => NotificationLevel::Warning,
            "error" => NotificationLevel::Error,
            _ => NotificationLevel::Info,
        };
        
        let notification = Notification::new(level, title.to_string(), message.to_string());
        self.publish(notification).await
    }
    
    /*
    /// 订阅通知频道（用于WebSocket服务）
    /// 暂时注释掉，因为Redis API变化
    pub async fn subscribe(&self) -> Result<redis::aio::PubSub> {
        let client = Client::open(self.redis.clone().into_inner())
            .context("Failed to create Redis client for subscription")?;
        
        let mut pubsub = client.get_async_pubsub()
            .await
            .context("Failed to create pubsub connection")?;
        
        pubsub.subscribe(&self.channel)
            .await
            .context("Failed to subscribe to notification channel")?;
        
        tracing::info!("📡 Subscribed to notification channel: {}", self.channel);
        
        Ok(pubsub)
    }
    */
}

impl NotificationLevel {
    fn emoji(&self) -> &'static str {
        match self {
            NotificationLevel::Info => "ℹ️",
            NotificationLevel::Success => "✅",
            NotificationLevel::Warning => "⚠️",
            NotificationLevel::Error => "❌",
        }
    }
}

impl Notification {
    fn level_emoji(&self) -> &'static str {
        self.level.emoji()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    #[ignore] // 需要Redis实例才能运行
    async fn test_notification_service() -> Result<()> {
        let service = NotificationService::new("redis://localhost:16380").await?;
        
        let notification = Notification::collection_started("boyar");
        service.publish(notification).await?;
        
        let history = service.get_history(10).await?;
        assert!(!history.is_empty());
        
        Ok(())
    }
}
