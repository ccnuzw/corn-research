//! PostgreSQL-backed schedules; tokio-cron-scheduler 0.9 evaluates cron in UTC.
use std::collections::HashMap;
use chrono::{DateTime, Utc};
use sea_orm::{ConnectionTrait, DatabaseConnection, DbBackend, FromQueryResult, Statement, TransactionTrait, Value};
use serde::{Deserialize, Serialize};
use tokio_cron_scheduler::{Job, JobScheduler};
use uuid::Uuid;
use crate::{collection_execution, notification::NotificationService};

fn sql(text: &str, values: Vec<Value>) -> Statement {
    Statement::from_sql_and_values(DbBackend::Postgres, text, values)
}

#[derive(Debug, Clone, Serialize, FromQueryResult)]
pub struct JobInfo {
    pub id: Uuid,
    pub name: String,
    pub collector_id: String,
    pub cron_expression: String,
    pub enabled: bool,
    pub description: Option<String>,
    pub status: String,
    pub last_run: Option<DateTime<Utc>>,
    pub last_error: Option<String>,
    pub total_runs: i64,
    pub success_count: i64,
    pub failed_count: i64,
    pub created_at: DateTime<Utc>,
    #[sea_orm(skip)]
    pub next_run: Option<DateTime<Utc>>,
    #[sea_orm(skip)]
    pub timezone: String,
}

#[derive(Debug, Serialize, FromQueryResult)]
pub struct Execution {
    pub id: Uuid,
    pub job_id: Uuid,
    pub trigger_type: String,
    pub status: String,
    pub started_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
    pub records_collected: i32,
    pub collection_run_id: Option<String>,
    pub error_message: Option<String>,
}

#[derive(Default, Deserialize)]
pub struct ExecutionsQuery {
    pub limit: Option<u64>,
    pub offset: Option<u64>,
    pub status: Option<String>,
    pub start_date: Option<DateTime<Utc>>,
    pub end_date: Option<DateTime<Utc>>,
}

pub struct JobManager {
    scheduler: JobScheduler,
    db: DatabaseConnection,
    notifications: NotificationService,
    runtime_ids: HashMap<Uuid, Uuid>,
}

impl JobManager {
    pub async fn new(db: DatabaseConnection, notifications: NotificationService) -> anyhow::Result<Self> {
        let scheduler = JobScheduler::new().await?;
        let mut manager = Self { scheduler, db, notifications, runtime_ids: HashMap::new() };
        // Single-backend Compose deployment: no previous worker can survive a restart.
        let txn = manager.db.begin().await?;
        txn.execute(sql("UPDATE job_executions SET status='failed', completed_at=NOW(), error_message='Backend restarted before execution completed' WHERE status='running'", vec![])).await?;
        txn.execute(sql("UPDATE scheduled_jobs SET status='failed', failed_count=failed_count+1, last_error='Backend restarted before execution completed' WHERE status='running'", vec![])).await?;
        txn.commit().await?;
        for job in manager.list_jobs().await? {
            if job.enabled { manager.register(&job).await?; }
        }
        Ok(manager)
    }

    pub async fn start(&self) -> anyhow::Result<()> {
        self.scheduler.start().await?;
        tracing::info!(jobs = self.runtime_ids.len(), timezone = "UTC", "Persistent scheduler started");
        Ok(())
    }

    async fn register(&mut self, info: &JobInfo) -> anyhow::Result<()> {
        let db = self.db.clone();
        let notifications = self.notifications.clone();
        let id = info.id;
        let job = Job::new_async(info.cron_expression.as_str(), move |_, _| {
            let db = db.clone();
            let notifications = notifications.clone();
            Box::pin(async move {
                if let Err(e) = launch(db, notifications, id, "scheduled").await {
                    tracing::warn!(job_id=%id, error=%e, "Scheduled execution skipped or failed to start");
                }
            })
        })?;
        let runtime = self.scheduler.add(job).await?;
        self.runtime_ids.insert(info.id, runtime);
        Ok(())
    }

    pub async fn list_jobs(&mut self) -> anyhow::Result<Vec<JobInfo>> {
        let mut jobs = JobInfo::find_by_statement(sql("SELECT * FROM scheduled_jobs ORDER BY created_at,id", vec![]))
            .all(&self.db).await?;
        for job in &mut jobs {
            job.timezone = "UTC".into();
            if let Some(runtime) = self.runtime_ids.get(&job.id) {
                job.next_run = self.scheduler.next_tick_for_job(*runtime).await?;
            }
        }
        Ok(jobs)
    }

    pub async fn add_collector_job(&mut self, name: String, collector_id: String, cron_expr: &str,
                                   description: Option<String>, enabled: bool) -> anyhow::Result<Uuid> {
        if name.trim().is_empty() { anyhow::bail!("name must not be empty"); }
        Job::new_async(cron_expr, |_, _| Box::pin(async {}))?;
        collection_execution::resolve_adapter(&self.db, &collector_id).await.map_err(anyhow::Error::msg)?;
        let id = Uuid::new_v4();
        self.db.execute(sql("INSERT INTO scheduled_jobs(id,name,collector_id,cron_expression,description,enabled) VALUES($1,$2,$3,$4,$5,$6)",
            vec![id.into(), name.into(), collector_id.into(), cron_expr.into(), description.into(), enabled.into()])).await?;
        if enabled {
            let job = self.get_job(id).await?;
            if let Err(e) = self.register(&job).await {
                self.db.execute(sql("DELETE FROM scheduled_jobs WHERE id=$1", vec![id.into()])).await?;
                return Err(e);
            }
        }
        Ok(id)
    }

    async fn get_job(&self, id: Uuid) -> anyhow::Result<JobInfo> {
        JobInfo::find_by_statement(sql("SELECT * FROM scheduled_jobs WHERE id=$1", vec![id.into()]))
            .one(&self.db).await?.ok_or_else(|| anyhow::anyhow!("Job not found"))
    }

    pub async fn remove_job(&mut self, id: Uuid) -> anyhow::Result<()> {
        let job = self.get_job(id).await?;
        if job.status == "running" { anyhow::bail!("Job is running"); }
        if let Some(runtime) = self.runtime_ids.remove(&id) { self.scheduler.remove(&runtime).await?; }
        self.db.execute(sql("DELETE FROM scheduled_jobs WHERE id=$1", vec![id.into()])).await?;
        Ok(())
    }

    pub async fn toggle_job(&mut self, id: Uuid, enabled: bool) -> anyhow::Result<()> {
        let mut job = self.get_job(id).await?;
        if job.enabled == enabled { return Ok(()); }
        if enabled {
            job.enabled = true;
            self.register(&job).await?;
        } else if let Some(runtime) = self.runtime_ids.remove(&id) {
            self.scheduler.remove(&runtime).await?;
        }
        self.db.execute(sql("UPDATE scheduled_jobs SET enabled=$2 WHERE id=$1", vec![id.into(), enabled.into()])).await?;
        Ok(())
    }

    pub async fn trigger_job(&self, id: Uuid) -> anyhow::Result<Uuid> {
        launch(self.db.clone(), self.notifications.clone(), id, "manual").await
    }

    pub async fn executions(&self, id: Uuid, q: ExecutionsQuery) -> anyhow::Result<Vec<Execution>> {
        self.get_job(id).await?;
        let limit = q.limit.unwrap_or(20);
        if !(1..=100).contains(&limit) || q.offset.unwrap_or(0) > i64::MAX as u64 {
            anyhow::bail!("limit must be 1..100 and offset must fit int64");
        }
        if q.status.as_deref().is_some_and(|s| !["running","success","failed"].contains(&s)) {
            anyhow::bail!("Invalid execution status");
        }
        if matches!((q.start_date,q.end_date), (Some(a),Some(b)) if a>b) {
            anyhow::bail!("start_date must not exceed end_date");
        }
        Ok(Execution::find_by_statement(sql(
            "SELECT * FROM job_executions WHERE job_id=$1 AND ($2::text IS NULL OR status=$2) AND ($3::timestamptz IS NULL OR started_at >= $3) AND ($4::timestamptz IS NULL OR started_at <= $4) ORDER BY started_at DESC,id DESC LIMIT $5 OFFSET $6",
            vec![id.into(), q.status.into(), q.start_date.into(), q.end_date.into(), (limit as i64).into(), (q.offset.unwrap_or(0) as i64).into()]
        )).all(&self.db).await?)
    }
}

async fn launch(db: DatabaseConnection, notifications: NotificationService, id: Uuid,
                trigger_type: &str) -> anyhow::Result<Uuid> {
    let txn = db.begin().await?;
    let row = txn.query_one(sql(
        "UPDATE scheduled_jobs SET status='running',last_run=NOW(),last_error=NULL,total_runs=total_runs+1 WHERE id=$1 AND status <> 'running' AND ($2='manual' OR enabled) RETURNING collector_id",
        vec![id.into(), trigger_type.into()])).await?
        .ok_or_else(|| anyhow::anyhow!("Job not found, disabled, or already running"))?;
    let collector: String = row.try_get("", "collector_id")?;
    let execution = Uuid::new_v4();
    txn.execute(sql("INSERT INTO job_executions(id,job_id,trigger_type,status) VALUES($1,$2,$3,'running')",
        vec![execution.into(), id.into(), trigger_type.into()])).await?;
    txn.commit().await?;
    tokio::spawn(async move {
        let result = async {
            let adapter = collection_execution::resolve_adapter(&db, &collector).await.map_err(anyhow::Error::msg)?;
            let run = collection_execution::start_run(&db, &adapter.id).await?;
            db.execute(sql("UPDATE job_executions SET collection_run_id=$2 WHERE id=$1",
                vec![execution.into(), run.id.clone().into()])).await?;
            collection_execution::execute_run(db.clone(), adapter, run, 100, true)
                .await.map_err(anyhow::Error::msg)
        }.await;
        let (status,count,error) = match result {
            Ok(count) => ("success", count as i32, None),
            Err(e) => ("failed", 0, Some(e.to_string())),
        };
        let finish = async {
            let txn = db.begin().await?;
            txn.execute(sql("UPDATE job_executions SET status=$2,completed_at=NOW(),records_collected=$3,error_message=$4 WHERE id=$1",
                vec![execution.into(), status.into(), count.into(), error.clone().into()])).await?;
            txn.execute(sql("UPDATE scheduled_jobs SET status=$2,last_error=$3,success_count=success_count+$4,failed_count=failed_count+$5 WHERE id=$1",
                vec![id.into(), status.into(), error.clone().into(), (if error.is_none(){1i64}else{0}).into(), (if error.is_some(){1i64}else{0}).into()])).await?;
            txn.commit().await
        }.await;
        if let Err(e) = finish { tracing::error!(job_id=%id, execution_id=%execution, error=%e, "Failed to persist execution outcome"); }
        if let Some(error) = error {
            tracing::error!(job_id=%id, execution_id=%execution, %collector, %error, "Scheduled collection failed");
            if let Err(e) = notifications.notify("定时采集失败", &format!("job={} execution={} collector={}: {}", id, execution, collector, error), "error").await {
                tracing::error!(error=%e, "Failed to publish scheduler failure notification");
            }
        } else {
            tracing::info!(job_id=%id, execution_id=%execution, records=count, "Scheduled collection completed");
        }
    });
    Ok(execution)
}
