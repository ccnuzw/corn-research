//! Shared, durable run lifecycle for synchronous collectors and async adapters.
use chrono::Utc;
use sea_orm::{
    ActiveModelTrait, ColumnTrait, DatabaseConnection, DbErr, EntityTrait,
    QueryFilter, QueryOrder, QuerySelect, Set, TransactionTrait, sea_query::Expr,
};
use crate::db::collection_entities::{adapter, record, run};
use crate::python_bridge::run_python_collector;
use crate::db::entities as raw_entity;
use sea_orm::sea_query::OnConflict;

async fn persist_sina_record(
    db: &DatabaseConnection, adapter: &adapter::Model,
    raw: &crate::python_bridge::RawRecord,
) -> Result<bool, DbErr> {
    let topic = match (raw.data_type.as_str(), raw.indicator.as_str()) {
        ("spot_price", "玉米现货价格") => "corn_spot_price",
        ("futures_price", "玉米期货价格") => "corn_futures_price",
        _ => return Err(DbErr::Custom("Unexpected Sina price indicator".into())),
    };
    if raw.metadata.get("is_mock").and_then(|v| v.as_bool()) != Some(false) {
        return Err(DbErr::Custom("Sina production records must be explicitly non-mock".into()));
    }
    let key = raw.metadata.get("record_key").and_then(|v| v.as_str())
        .filter(|k| !k.is_empty()).ok_or_else(|| DbErr::Custom("Missing price series key".into()))?;
    let date = chrono::NaiveDate::parse_from_str(&raw.business_date, "%Y-%m-%d")
        .map_err(|e| DbErr::Custom(e.to_string()))?;
    let value = rust_decimal::Decimal::from_f64_retain(raw.value)
        .filter(|v| *v > rust_decimal::Decimal::ZERO)
        .ok_or_else(|| DbErr::Custom("Invalid price".into()))?;
    let now = Utc::now().fixed_offset();
    let txn = db.begin().await?;
    let inserted = record::Entity::insert(record::ActiveModel {
        id: Set(uuid::Uuid::new_v4().to_string()), adapter_id: Set(adapter.id.clone()),
        business_date: Set(date), value: Set(Some(value)), unit: Set(Some(raw.unit.clone())),
        topic_name: Set(Some(topic.into())), record_key: Set(key.into()),
        indicator: Set(Some(raw.indicator.clone())), region: Set(Some(raw.region.clone())),
        metadata: Set(Some(raw.metadata.clone())), quality_grade: Set(Some("B".into())),
        source_url: Set(Some(raw.source_url.clone())), collected_at: Set(now),
        ..Default::default()
    }).on_conflict(OnConflict::columns([
        record::Column::AdapterId, record::Column::BusinessDate,
        record::Column::TopicName, record::Column::RecordKey,
    ]).do_nothing().to_owned()).exec_without_returning(&txn).await? > 0;
    // Keep the legacy latest-data API and adapter record API consistent, atomically per price.
    let dedup_key = serde_json::json!([adapter.id, raw.business_date, topic, key]).to_string();
    raw_entity::Entity::insert(raw_entity::ActiveModel {
        id: Set(uuid::Uuid::new_v4()), collector_id: Set(adapter.id.clone()),
        business_date: Set(date), indicator_name: Set(raw.indicator.clone()), value: Set(value),
        unit: Set(raw.unit.clone()), region: Set(Some(raw.region.clone())),
        source_url: Set(raw.source_url.clone()), original_text: Set(raw.original_text.clone()),
        dedup_key: Set(dedup_key), collected_at: Set(now), ..Default::default()
    }).on_conflict(OnConflict::column(raw_entity::Column::DedupKey)
        .do_nothing().to_owned()).exec_without_returning(&txn).await?;
    txn.commit().await?;
    Ok(inserted)
}

pub type CollectionRun = run::Model;

pub async fn resolve_adapter(db: &DatabaseConnection, collector: &str) -> Result<adapter::Model, String> {
    let script = match collector {
        "boyar" => "boyar_production",
        "sina" => "sina_production",
        other => other,
    };
    let adapters = adapter::Entity::find()
        .filter(adapter::Column::ScriptFile.eq(script))
        .order_by_asc(adapter::Column::Id).limit(2).all(db).await
        .map_err(|e| e.to_string())?;
    if adapters.len() != 1 {
        return Err(format!("Collector {} requires exactly one configured adapter; use /api/adapters/:id/run", collector));
    }
    adapters.into_iter().next().ok_or_else(|| format!("Collector {} has no configured adapter", collector))
}

pub async fn start_run(db: &DatabaseConnection, adapter_id: &str) -> Result<CollectionRun, DbErr> {
    run::ActiveModel {
        id: Set(uuid::Uuid::new_v4().to_string()),
        adapter_id: Set(adapter_id.to_string()),
        started_at: Set(Utc::now().into()),
        status: Set(Some("running".into())),
        records_collected: Set(0),
        new_records: Set(Some(0)),
        duplicate_records: Set(Some(0)),
        failed_records: Set(Some(0)),
        ..Default::default()
    }.insert(db).await
}

async fn finish_run(
    db: &DatabaseConnection, history: CollectionRun,
    collected: i32, new: i32, duplicates: i32, failed: i32, error: Option<String>,
) -> Result<(), DbErr> {
    let txn = db.begin().await?;
    let adapter_id = history.adapter_id.clone();
    let mut update: run::ActiveModel = history.into();
    let ok = error.is_none() && failed == 0;
    update.status = Set(Some(if ok { "success" } else { "failed" }.into()));
    update.completed_at = Set(Some(Utc::now().into()));
    update.records_collected = Set(collected);
    update.new_records = Set(Some(new));
    update.duplicate_records = Set(Some(duplicates));
    update.failed_records = Set(Some(failed));
    update.error_message = Set(error.clone());
    update.update(&txn).await?;
    let counter = if ok { adapter::Column::SuccessfulRuns } else { adapter::Column::FailedRuns };
    adapter::Entity::update_many()
        .col_expr(adapter::Column::TotalRuns, Expr::col(adapter::Column::TotalRuns).add(1))
        .col_expr(counter, Expr::col(counter).add(1))
        .col_expr(adapter::Column::LastRunAt, Expr::value(Utc::now().fixed_offset()))
        .col_expr(adapter::Column::LastError, Expr::value(error))
        .filter(adapter::Column::Id.eq(adapter_id)).exec(&txn).await?;
    txn.commit().await
}

pub async fn execute_run(
    db: DatabaseConnection, adapter: adapter::Model, history: CollectionRun,
    max_items: u32, persist: bool,
) -> Result<usize, String> {
    let result = run_python_collector(&adapter.script_file, Some(max_items)).await;
    let (mut new, mut duplicates, mut failed) = (0, 0, 0);
    let mut error = None;
    let count = match result {
        Ok(records) => {
            let count = records.len();
            if persist {
                for raw in records {
                    if adapter.script_file == "sina_production" {
                        match persist_sina_record(&db, &adapter, &raw).await {
                            Ok(true) => new += 1,
                            Ok(false) => duplicates += 1,
                            Err(e) => {
                                tracing::error!(run_id = %history.id, "Sina record insert failed: {}", e);
                                failed += 1;
                            }
                        }
                        continue;
                    }
                    let date = chrono::NaiveDate::parse_from_str(&raw.business_date, "%Y-%m-%d");
                    let value = rust_decimal::Decimal::from_f64_retain(raw.value);
                    let (date, value) = match (date, value) {
                        (Ok(date), Some(value)) => (date, value),
                        _ => { failed += 1; continue; }
                    };
                    let model = record::ActiveModel {
                        id: Set(uuid::Uuid::new_v4().to_string()),
                        adapter_id: Set(adapter.id.clone()), business_date: Set(date),
                        value: Set(Some(value)), unit: Set(Some(raw.unit)),
                        topic_name: Set(Some(adapter.topic_name.clone())),
                        source_url: Set(Some(raw.source_url)),
                        source_html_path: Set(raw.metadata.get("html_path").and_then(|v| v.as_str())
                            .filter(|p| !p.is_empty()).map(str::to_string)),
                        collected_at: Set(Utc::now().into()),
                        ..Default::default()
                    };
                    match model.insert(&db).await {
                        Ok(_) => new += 1,
                        Err(e) if matches!(e.sql_err(), Some(sea_orm::SqlErr::UniqueConstraintViolation(_))) => duplicates += 1,
                        Err(e) => {
                            tracing::error!(run_id = %history.id, "Record insert failed: {}", e);
                            failed += 1;
                        }
                    }
                }
            }
            if failed > 0 { error = Some(format!("{} records failed validation or insertion", failed)); }
            count
        }
        Err(e) => { error = Some(e); 0 }
    };
    let run_id = history.id.clone();
    finish_run(&db, history, count as i32, new, duplicates, failed, error.clone()).await
        .map_err(|e| format!("Failed to finish run {}: {}", run_id, e))?;
    tracing::info!(%run_id, collected = count, new_records = new, duplicates, failed,
        status = if error.is_none() { "success" } else { "failed" }, "Collection run finished");
    match error { Some(e) => Err(e), None => Ok(count) }
}

pub async fn recover_interrupted_runs(db: &DatabaseConnection) -> Result<(), DbErr> {
    // This Compose deployment has one backend instance; no older worker survives startup.
    for history in run::Entity::find().filter(run::Column::Status.eq("running")).all(db).await? {
        finish_run(db, history, 0, 0, 0, 0, Some("Backend restarted before collection completed".into())).await?;
    }
    Ok(())
}
