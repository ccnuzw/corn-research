//! Durable queue for the single-backend Compose deployment. Queued jobs survive restart;
//! interrupted running jobs fail explicitly instead of replaying non-transactional site scans.
use axum::{extract::{Path, State}, http::StatusCode, Json};
use chrono::{DateTime, Utc};
use sea_orm::{ConnectionTrait, DatabaseConnection, DbBackend, DbErr, EntityTrait,
    FromQueryResult, Statement, TransactionTrait, Value};
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use crate::{AppState, errors::CornError, collection_execution, db::collection_entities::adapter,
    python_bridge::ProgressEvent};

fn sql(text: &str, values: Vec<Value>) -> Statement {
    Statement::from_sql_and_values(DbBackend::Postgres, text, values)
}

#[derive(Debug, Clone, Serialize, FromQueryResult)]
pub struct AsyncJob {
    pub id: Uuid,
    pub collector_name: String,
    pub adapter_id: String,
    pub run_id: Option<String>,
    pub max_items: i32,
    pub status: String,
    pub progress: i32,
    pub phase: String,
    pub details: serde_json::Value,
    pub result: Option<serde_json::Value>,
    pub error_message: Option<String>,
    pub created_at: DateTime<Utc>,
    pub started_at: Option<DateTime<Utc>>,
    pub completed_at: Option<DateTime<Utc>>,
    pub updated_at: DateTime<Utc>,
}

pub struct Repository;
impl Repository {
    pub async fn get(db: &DatabaseConnection, id: Uuid) -> Result<Option<AsyncJob>, DbErr> {
        AsyncJob::find_by_statement(sql("SELECT * FROM async_jobs WHERE id=$1", vec![id.into()]))
            .one(db).await
    }

    pub async fn list(db: &DatabaseConnection) -> Result<Vec<AsyncJob>, DbErr> {
        AsyncJob::find_by_statement(sql("SELECT * FROM async_jobs ORDER BY created_at DESC LIMIT 100", vec![]))
            .all(db).await
    }
    pub async fn enqueue(db: &DatabaseConnection, collector: String, adapter: String, max: i32)
        -> Result<Uuid, DbErr> {
        let id = Uuid::new_v4();
        db.execute(sql("INSERT INTO async_jobs(id,collector_name,adapter_id,max_items) VALUES($1,$2,$3,$4)",
            vec![id.into(), collector.into(), adapter.into(), max.into()])).await?;
        Ok(id)
    }

    async fn claim(db: &DatabaseConnection) -> Result<Option<(AsyncJob, collection_execution::CollectionRun)>, DbErr> {
        let txn = db.begin().await?;
        let row = txn.query_one(sql("SELECT id FROM async_jobs WHERE status='queued' ORDER BY created_at,id FOR UPDATE SKIP LOCKED LIMIT 1", vec![])).await?;
        let Some(row) = row else { txn.commit().await?; return Ok(None); };
        let id: Uuid = row.try_get("", "id")?;
        let job = AsyncJob::find_by_statement(sql("SELECT * FROM async_jobs WHERE id=$1", vec![id.into()]))
            .one(&txn).await?.ok_or_else(|| DbErr::Custom("Queued job disappeared".into()))?;
        let run = collection_execution::start_run(&txn, &job.adapter_id).await?;
        txn.execute(sql("UPDATE async_jobs SET status='running',phase='starting',progress=1,run_id=$2,started_at=NOW(),updated_at=NOW() WHERE id=$1",
            vec![id.into(), run.id.clone().into()])).await?;
        txn.commit().await?;
        Ok(Some((job, run)))
    }

    async fn progress(db: &DatabaseConnection, id: Uuid, event: ProgressEvent) -> Result<(), DbErr> {
        let percent = progress_percent(&event);
        let details = serde_json::to_value(&event).map_err(|e| DbErr::Custom(e.to_string()))?;
        db.execute(sql("UPDATE async_jobs SET progress=GREATEST(progress,$2),phase=$3,details=$4,updated_at=NOW() WHERE id=$1 AND status='running'",
            vec![id.into(), percent.into(), event.phase.into(), details.into()])).await?;
        Ok(())
    }

    async fn finish(db: &DatabaseConnection, id: Uuid, result: Result<usize, String>) -> Result<(), DbErr> {
        let (status, error, value) = match result {
            Ok(count) => ("succeeded", None, Some(serde_json::json!({"records_collected": count}))),
            Err(error) => ("failed", Some(error), None),
        };
        db.execute(sql("UPDATE async_jobs SET status=$2,phase=$2,progress=CASE WHEN $2='succeeded' THEN 100 ELSE progress END,result=$3,error_message=$4,completed_at=NOW(),updated_at=NOW() WHERE id=$1 AND status='running'",
            vec![id.into(), status.into(), value.into(), error.into()])).await?;
        Ok(())
    }
}

fn progress_percent(event: &ProgressEvent) -> i32 {
    match event.phase.as_str() {
        "scanning" if event.total > 0 => 5 + (80u64 * event.completed.min(event.total) as u64 / event.total as u64) as i32,
        "collected" => 88,
        "persisting" => 90,
        _ => 2,
    }
}

#[derive(Deserialize)]
pub struct CreateRequest {
    #[serde(alias="collector_id")]
    collector_name: String,
    max_items: Option<i32>,
}

pub async fn submit(State(state): State<AppState>, Json(request): Json<CreateRequest>)
    -> Result<(StatusCode, Json<serde_json::Value>), CornError> {
    let max = request.max_items.unwrap_or(100);
    if request.collector_name.trim().is_empty() || !(1..=1000).contains(&max) {
        return Err(CornError::Validation("collector_name is required; max_items must be 1..1000".into()));
    }
    let adapter = collection_execution::resolve_adapter(&state.db, &request.collector_name)
        .await.map_err(CornError::Validation)?;
    match Repository::enqueue(&state.db, request.collector_name, adapter.id, max).await {
        Ok(id) => Ok((StatusCode::ACCEPTED, Json(serde_json::json!({
            "success": true, "data": {"job_id": id, "status": "queued", "status_url": format!("/api/jobs/{}", id)},
            "message": "Collection queued",
        })))),
        Err(e) if matches!(e.sql_err(), Some(sea_orm::SqlErr::UniqueConstraintViolation(_))) =>
            Err(CornError::Conflict("An async collection is already queued/running for this adapter".into())),
        Err(e) => Err(CornError::Internal(format!("Failed to enqueue collection: {}", e))),
    }
}

pub async fn get(State(state): State<AppState>, Path(id): Path<Uuid>)
    -> Result<Json<serde_json::Value>, CornError> {
    let job = Repository::get(&state.db, id).await.map_err(|e| CornError::Internal(e.to_string()))?
        .ok_or_else(|| CornError::NotFound("Async job not found".into()))?;
    Ok(Json(serde_json::json!({"success": true, "data": job, "message": null})))
}

pub async fn list(State(state): State<AppState>)
    -> Result<Json<serde_json::Value>, CornError> {
    let jobs = Repository::list(&state.db).await.map_err(|e| CornError::Internal(e.to_string()))?;
    Ok(Json(serde_json::json!({
        "success": true,
        "data": jobs,
        "total": jobs.len()
    })))
}

pub async fn start(db: DatabaseConnection) -> anyhow::Result<()> {
    // Collection-run restart recovery is executed first in main. Reconcile a run
    // finalized before a crash but whose async job had not yet been finalized.
    db.execute(sql("UPDATE async_jobs j SET status=CASE WHEN r.status='success' THEN 'succeeded' ELSE 'failed' END,phase=CASE WHEN r.status='success' THEN 'succeeded' ELSE 'failed' END,progress=CASE WHEN r.status='success' THEN 100 ELSE j.progress END,result=CASE WHEN r.status='success' THEN jsonb_build_object('records_collected',r.records_collected) ELSE NULL END,error_message=CASE WHEN r.status='success' THEN NULL ELSE COALESCE(r.error_message,'Backend restarted before async job completed') END,completed_at=NOW(),updated_at=NOW() FROM collection_runs r WHERE j.run_id=r.id AND j.status='running'", vec![])).await?;
    db.execute(sql("UPDATE async_jobs SET status='failed',phase='failed',error_message='Backend restarted before async job completed',completed_at=NOW(),updated_at=NOW() WHERE status='running'", vec![])).await?;
    // Fixed-size workers bound the number of Python processes; durable DB polling
    // avoids losing accepted jobs if the client disconnects or the process restarts.
    for worker in 0..2 {
        let db = db.clone();
        tokio::spawn(async move {
            loop {
                match Repository::claim(&db).await {
                    Ok(Some((job, run))) => execute(db.clone(), job, run).await,
                    Ok(None) => tokio::time::sleep(std::time::Duration::from_millis(250)).await,
                    Err(error) => {
                        tracing::error!(worker, %error, "Async queue claim failed");
                        tokio::time::sleep(std::time::Duration::from_secs(2)).await;
                    }
                }
            }
        });
    }
    Ok(())
}

async fn execute(db: DatabaseConnection, job: AsyncJob, run: collection_execution::CollectionRun) {
    let id = job.id;
    let (sender, mut receiver) = tokio::sync::mpsc::unbounded_channel();
    let progress_db = db.clone();
    let updates = tokio::spawn(async move {
        while let Some(event) = receiver.recv().await {
            if let Err(error) = Repository::progress(&progress_db, id, event).await {
                tracing::error!(job_id=%id, %error, "Async job progress update failed");
            }
        }
    });
    let adapter = adapter::Entity::find_by_id(job.adapter_id.clone()).one(&db).await;
    let result = match adapter {
        Ok(Some(adapter)) => {
            let db = db.clone();
            match tokio::spawn(collection_execution::execute_run_with_progress(
                db, adapter, run.clone(), job.max_items as u32, true, Some(sender),
            )).await {
                Ok(result) => result,
                Err(error) => Err(format!("Collection worker stopped unexpectedly: {}", error)),
            }
        }
        other => { drop(sender); Err(format!("Async adapter unavailable: {:?}", other)) }
    };
    if let Err(error) = updates.await { tracing::error!(job_id=%id, %error, "Async progress consumer failed"); }
    if let Err(error) = &result {
        tracing::error!(job_id=%id, %error, "Async collection failed");
        // Cover failures before execute_run or task panic. Do not rewrite a finalized run.
        if let Err(db_error) = db.execute(sql("UPDATE collection_runs SET status='failed',completed_at=NOW(),error_message=$2 WHERE id=$1 AND status='running'",
            vec![run.id.into(), error.clone().into()])).await {
            tracing::error!(job_id=%id, %db_error, "Failed to finalize interrupted collection run");
        }
    }
    // Small retry budget for a transient DB interruption during terminal-state recording.
    for attempt in 0..3 {
        match Repository::finish(&db, id, result.clone()).await {
            Ok(()) => return,
            Err(error) => {
                tracing::error!(job_id=%id, attempt, %error, "Async job finalization failed");
                tokio::time::sleep(std::time::Duration::from_secs(1)).await;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn progress_is_bounded_and_only_terminal_success_reaches_100() {
        for (phase, done, total, expected) in [("scanning",0,150,5),("scanning",75,150,45),
            ("scanning",300,150,85),("collected",0,0,88),("persisting",0,0,90)] {
            let e = ProgressEvent { phase: phase.into(), completed: done, total, details: Default::default() };
            assert_eq!(progress_percent(&e), expected);
        }
    }
}
