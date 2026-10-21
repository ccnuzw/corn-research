//! Job Manager - 定时任务管理器
//!
//! 基于tokio-cron-scheduler实现定时任务调度

use tokio_cron_scheduler::{Job, JobScheduler, JobSchedulerError};
use std::sync::Arc;
use serde::{Serialize, Deserialize};
use uuid::Uuid;
use chrono::{DateTime, Utc};
use std::collections::HashMap;

/// 定时任务管理器
pub struct JobManager {
    scheduler: JobScheduler,
    job_metadata: Arc<tokio::sync::RwLock<HashMap<Uuid, JobMetadata>>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JobInfo {
    pub id: String,
    pub name: String,
    pub collector_id: Option<String>,
    pub cron_expression: String,
    pub enabled: bool,
    pub description: Option<String>,
    pub last_run: Option<DateTime<Utc>>,
    pub next_run: Option<DateTime<Utc>>,
    pub total_runs: u32,
    pub success_count: u32,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone)]
struct JobMetadata {
    name: String,
    collector_id: Option<String>,
    cron_expression: String,
    description: Option<String>,
    created_at: DateTime<Utc>,
    last_run: Option<DateTime<Utc>>,
    total_runs: u32,
    success_count: u32,
    enabled: bool,
}

impl JobManager {
    /// 创建新的任务管理器
    pub async fn new() -> Result<Self, JobSchedulerError> {
        let scheduler = JobScheduler::new().await?;
        
        tracing::info!("✅ Job scheduler initialized");
        
        Ok(Self { 
            scheduler,
            job_metadata: Arc::new(tokio::sync::RwLock::new(HashMap::new())),
        })
    }
    
    /// 启动调度器
    pub async fn start(&self) -> Result<(), JobSchedulerError> {
        self.scheduler.start().await?;
        tracing::info!("🚀 Job scheduler started");
        Ok(())
    }
    
    /// 停止调度器
    pub async fn shutdown(&mut self) -> Result<(), JobSchedulerError> {
        self.scheduler.shutdown().await?;
        tracing::info!("🛑 Job scheduler stopped");
        Ok(())
    }
    
    /// 添加每日采集任务（每天8:00执行）
    /// 
    /// # Arguments
    /// * `collector_ids` - 采集器ID列表（按顺序串行执行）
    pub async fn add_daily_collection_job(
        &self,
        collector_ids: Vec<String>,
    ) -> Result<Uuid, JobSchedulerError> {
        let metadata = self.job_metadata.clone();
        let job_name = "Daily Collection".to_string();
        let cron_expr = "0 0 8 * * *".to_string();
        
        let job = Job::new_async("0 0 8 * * *", move |uuid, _l| {
            let ids = collector_ids.clone();
            let meta = metadata.clone();
            Box::pin(async move {
                tracing::info!("🌅 Daily collection job started");
                
                // 更新运行计数
                {
                    let mut map = meta.write().await;
                    if let Some(m) = map.get_mut(&uuid) {
                        m.last_run = Some(Utc::now());
                        m.total_runs += 1;
                    }
                }
                
                let mut success = true;
                for collector_id in &ids {
                    tracing::info!("🔄 Running collector: {}", collector_id);
                    
                    // 调用采集器（通过Python桥接）
                    match run_collector(collector_id).await {
                        Ok(count) => {
                            tracing::info!("✅ Collector {} completed: {} records", collector_id, count);
                        }
                        Err(e) => {
                            tracing::error!("❌ Collector {} failed: {}", collector_id, e);
                            success = false;
                            
                            // 重试逻辑：最多3次，每次间隔1分钟
                            for retry in 1..=3 {
                                tracing::warn!("🔄 Retry {}/3 for collector {}", retry, collector_id);
                                tokio::time::sleep(tokio::time::Duration::from_secs(60)).await;
                                
                                match run_collector(collector_id).await {
                                    Ok(count) => {
                                        tracing::info!("✅ Collector {} succeeded on retry {}: {} records", 
                                            collector_id, retry, count);
                                        success = true;
                                        break;
                                    }
                                    Err(e) => {
                                        tracing::error!("❌ Retry {}/3 failed: {}", retry, e);
                                        if retry == 3 {
                                            tracing::error!("❌ All retries exhausted for collector {}", collector_id);
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                
                // 更新成功计数
                if success {
                    let mut map = meta.write().await;
                    if let Some(m) = map.get_mut(&uuid) {
                        m.success_count += 1;
                    }
                }
                
                tracing::info!("🎉 Daily collection job completed");
            })
        })?;
        
        let job_id = self.scheduler.add(job).await?;
        
        // 存储元数据
        self.job_metadata.write().await.insert(job_id, JobMetadata {
            name: job_name,
            collector_id: None,
            cron_expression: cron_expr,
            description: Some("每日定时采集任务".to_string()),
            created_at: Utc::now(),
            last_run: None,
            total_runs: 0,
            success_count: 0,
            enabled: true,
        });
        
        tracing::info!("📅 Daily collection job added: {}", job_id);
        
        Ok(job_id)
    }
    
    /// 添加自定义采集器任务
    pub async fn add_collector_job(
        &self,
        name: String,
        collector_id: String,
        cron_expr: &str,
        description: Option<String>,
    ) -> Result<Uuid, JobSchedulerError> {
        let metadata = self.job_metadata.clone();
        let cid = collector_id.clone();
        
        let job = Job::new_async(cron_expr, move |uuid, _l| {
            let collector = cid.clone();
            let meta = metadata.clone();
            Box::pin(async move {
                tracing::info!("🔄 Scheduled job running collector: {}", collector);
                
                // 更新运行计数
                {
                    let mut map = meta.write().await;
                    if let Some(m) = map.get_mut(&uuid) {
                        m.last_run = Some(Utc::now());
                        m.total_runs += 1;
                    }
                }
                
                match run_collector(&collector).await {
                    Ok(count) => {
                        tracing::info!("✅ Collector {} completed: {} records", collector, count);
                        
                        // 更新成功计数
                        {
                            let mut map = meta.write().await;
                            if let Some(m) = map.get_mut(&uuid) {
                                m.success_count += 1;
                            }
                        }
                    }
                    Err(e) => {
                        tracing::error!("❌ Collector {} failed: {}", collector, e);
                    }
                }
            })
        })?;
        
        let job_id = self.scheduler.add(job).await?;
        
        // 存储元数据
        self.job_metadata.write().await.insert(job_id, JobMetadata {
            name: name.clone(),
            collector_id: Some(collector_id),
            cron_expression: cron_expr.to_string(),
            description,
            created_at: Utc::now(),
            last_run: None,
            total_runs: 0,
            success_count: 0,
            enabled: true,
        });
        
        tracing::info!("📅 Custom collector job '{}' added: {}", name, job_id);
        
        Ok(job_id)
    }
    
    /// 删除任务
    pub async fn remove_job(&self, job_id: Uuid) -> Result<(), JobSchedulerError> {
        self.scheduler.remove(&job_id).await?;
        self.job_metadata.write().await.remove(&job_id);
        tracing::info!("🗑️ Job removed: {}", job_id);
        Ok(())
    }
    
    /// 启用/禁用任务
    pub async fn toggle_job(&self, job_id: Uuid, enabled: bool) -> Result<(), JobSchedulerError> {
        if let Some(metadata) = self.job_metadata.write().await.get_mut(&job_id) {
            metadata.enabled = enabled;
            tracing::info!("🔄 Job {} {}", job_id, if enabled { "enabled" } else { "disabled" });
        }
        Ok(())
    }
    
    /// 手动触发任务
    pub async fn trigger_job(&mut self, job_id: Uuid) -> Result<(), JobSchedulerError> {
        // 获取任务的采集器ID
        let collector_id = {
            let metadata = self.job_metadata.read().await;
            metadata.get(&job_id)
                .and_then(|m| m.collector_id.clone())
        };
        
        if let Some(cid) = collector_id {
            tracing::info!("🔄 Manually triggering job {}: collector {}", job_id, cid);
            
            // 异步执行采集器
            tokio::spawn(async move {
                match run_collector(&cid).await {
                    Ok(count) => {
                        tracing::info!("✅ Manual trigger completed: {} records", count);
                    }
                    Err(e) => {
                        tracing::error!("❌ Manual trigger failed: {}", e);
                    }
                }
            });
            
            Ok(())
        } else {
            tracing::warn!("⚠️ Job {} has no associated collector", job_id);
            Err(JobSchedulerError::UpdateJobData)
        }
    }
    
    /// 列出所有任务
    pub async fn list_jobs(&self) -> Vec<JobInfo> {
        let metadata = self.job_metadata.read().await;
        
        metadata.iter().map(|(id, meta)| {
            JobInfo {
                id: id.to_string(),
                name: meta.name.clone(),
                collector_id: meta.collector_id.clone(),
                cron_expression: meta.cron_expression.clone(),
                enabled: meta.enabled,
                description: meta.description.clone(),
                last_run: meta.last_run,
                next_run: None, // TODO: 计算下次运行时间
                total_runs: meta.total_runs,
                success_count: meta.success_count,
                created_at: meta.created_at,
            }
        }).collect()
    }
}

/// 执行采集器（TODO: 与python_bridge集成）
async fn run_collector(collector_id: &str) -> Result<usize, anyhow::Error> {
    // 这里需要调用实际的Python采集器
    // 暂时返回模拟结果
    tracing::debug!("Simulating collector run: {}", collector_id);
    
    // 模拟延迟
    tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
    
    // 返回模拟的采集条数
    Ok(42)
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_job_manager_creation() {
        let manager = JobManager::new().await.unwrap();
        manager.start().await.unwrap();
        
        // 测试添加任务
        let job_id = manager.add_daily_collection_job(vec![
            "boyar".to_string(),
            "sina".to_string(),
        ]).await.unwrap();
        
        assert_ne!(job_id, Uuid::nil());
        
        // 测试列出任务
        let jobs = manager.list_jobs().await;
        assert_eq!(jobs.len(), 1);
    }
}
