//! Real PostgreSQL transaction tests. Explicit opt-in; never use DATABASE_URL.
use super::*;
use sea_orm::{ConnectOptions, ConnectionTrait, Database, DbBackend, Statement, PaginatorTrait};
use crate::python_bridge::{CollectorBatch, RawRecord};

async fn database() -> DatabaseConnection {
    let url = std::env::var("TEST_DCE_DATABASE_URL").expect("set isolated TEST_DCE_DATABASE_URL");
    assert!(url.split('?').next().unwrap().ends_with("/corn_dce_test"),
        "DCE tests require a dedicated corn_dce_test database");
    let admin = Database::connect(&url).await.unwrap();
    let schema = format!("dce_test_{}", uuid::Uuid::new_v4().simple());
    admin.execute_unprepared(&format!("CREATE SCHEMA {schema}")).await.unwrap();
    let mut options = ConnectOptions::new(url);
    options.set_schema_search_path(schema).sqlx_logging(false);
    let db = Database::connect(options).await.unwrap();
    for sql in [
        include_str!("../../migrations/001_create_raw_table.sql"),
        include_str!("../../migrations/003_create_collection_management.sql"),
        include_str!("../../migrations/006_collection_run_counts.sql"),
        include_str!("../../migrations/007_sina_corn_prices.sql"),
        include_str!("../../migrations/010_dce_corn_prices.sql"),
    ] {
        db.execute_unprepared(sql).await.unwrap();
    }
    db
}

fn fixture(contract: &str) -> RawRecord {
    // Synthetic transaction fixture, confined to an ephemeral test database.
    RawRecord {
        business_date: "2026-10-21".into(), data_type: "futures_price".into(),
        indicator: "玉米期货价格".into(), value: 2130.0, unit: "元/吨".into(),
        region: "大连商品交易所".into(),
        source_url: "http://www.dce.com.cn/dcereport/publicweb/dailystat/dayQuotes".into(),
        original_text: Some("SYNTHETIC TEST FIXTURE".into()),
        collected_at: "2026-10-21T12:00:00Z".into(), published_at: None,
        metadata: serde_json::json!({"is_mock": false, "record_key": contract,
            "contract": contract, "exchange": "DCE", "price_field": "close"}),
    }
}

async fn dce(db: &DatabaseConnection) -> adapter::Model {
    resolve_adapter(db, "dce").await.unwrap()
}

#[tokio::test]
#[ignore = "requires an ephemeral TEST_DCE_DATABASE_URL"]
async fn dce_alias_and_idempotent_migration() {
    let db = database().await;
    db.execute_unprepared(include_str!("../../migrations/010_dce_corn_prices.sql")).await.unwrap();
    assert_eq!(dce(&db).await.id, "adapter_dce_futures");
    assert_eq!(resolve_adapter(&db, "dce_production").await.unwrap().id, "adapter_dce_futures");
    assert!(resolve_adapter(&db, "not_configured").await.is_err());
}

#[tokio::test]
#[ignore = "requires an ephemeral TEST_DCE_DATABASE_URL"]
async fn multiple_contracts_persist_to_both_tables_and_deduplicate() {
    let db = database().await;
    let adapter = dce(&db).await;
    for expected_new in [2, 0] {
        let run = start_run(&db, &adapter.id).await.unwrap();
        let id = run.id.clone();
        assert_eq!(complete_run(db.clone(), adapter.clone(), run, true, Ok(CollectorBatch {
            records: vec![fixture("C2701"), fixture("C2705")], cursor_updates: vec![],
        })).await.unwrap(), 2);
        let history = run::Entity::find_by_id(id).one(&db).await.unwrap().unwrap();
        assert_eq!(history.status.as_deref(), Some("success"));
        assert!(history.completed_at.is_some());
        assert_eq!(history.records_collected, 2);
        assert_eq!(history.new_records, Some(expected_new));
        assert_eq!(history.duplicate_records, Some(2 - expected_new));
        assert_eq!(history.failed_records, Some(0));
    }
    let rows = record::Entity::find().all(&db).await.unwrap();
    assert_eq!(rows.len(), 2);
    assert!(rows.iter().all(|r| r.quality_grade.as_deref() == Some("A")
        && r.topic_name.as_deref() == Some("corn_futures_price")));
    assert_ne!(rows[0].record_key, rows[1].record_key);
    assert_eq!(raw_entity::Entity::find().count(&db).await.unwrap(), 2);
    let adapter = dce(&db).await;
    assert_eq!((adapter.total_runs, adapter.successful_runs, adapter.failed_runs), (2, 2, 0));
}

#[tokio::test]
#[ignore = "requires an ephemeral TEST_DCE_DATABASE_URL"]
async fn invalid_dce_prices_dates_and_provenance_never_write() {
    let db = database().await;
    let adapter = dce(&db).await;
    let mut invalid = Vec::new();
    for value in [f64::NAN, f64::INFINITY, -1.0, 0.0] {
        let mut raw = fixture("C2701"); raw.value = value; invalid.push(raw);
    }
    let mut raw = fixture("C2713"); invalid.push(raw.clone());
    raw = fixture("C2701"); raw.metadata["is_mock"] = true.into(); invalid.push(raw.clone());
    raw = fixture("C2701"); raw.metadata["record_key"] = "".into(); invalid.push(raw.clone());
    raw = fixture("C2701"); raw.metadata["exchange"] = "OTHER".into(); invalid.push(raw.clone());
    raw = fixture("C2701"); raw.metadata["record_key"] = "C2705".into(); invalid.push(raw.clone());
    raw = fixture("C2701"); raw.source_url = "https://untrusted.invalid".into(); invalid.push(raw.clone());
    raw = fixture("C2701"); raw.unit = "USD".into(); invalid.push(raw.clone());
    raw = fixture("C2701"); raw.business_date = "2026-02-30".into(); invalid.push(raw.clone());
    raw = fixture("C2701"); raw.indicator = "other".into(); invalid.push(raw);
    for raw in invalid {
        assert!(persist_price_record(&db, &adapter, &raw).await.is_err());
    }
    assert_eq!(record::Entity::find().count(&db).await.unwrap(), 0);
    assert_eq!(raw_entity::Entity::find().count(&db).await.unwrap(), 0);
}

#[tokio::test]
#[ignore = "requires an ephemeral TEST_DCE_DATABASE_URL"]
async fn raw_insert_failure_rolls_back_collection_insert() {
    let db = database().await;
    let adapter = dce(&db).await;
    db.execute_unprepared("ALTER TABLE raw_collection_records ADD CONSTRAINT injected_failure CHECK (value < 0)").await.unwrap();
    assert!(persist_price_record(&db, &adapter, &fixture("C2701")).await.is_err());
    assert_eq!(record::Entity::find().count(&db).await.unwrap(), 0);
    assert_eq!(raw_entity::Entity::find().count(&db).await.unwrap(), 0);
}

#[tokio::test]
#[ignore = "requires an ephemeral TEST_DCE_DATABASE_URL and isolated REDIS_URL"]
async fn validation_failure_blocks_cursor_acknowledgement() {
    let db = database().await;
    let adapter = dce(&db).await;
    let redis_url = std::env::var("TEST_DCE_REDIS_URL").expect("set isolated TEST_DCE_REDIS_URL");
    assert_eq!(std::env::var("REDIS_URL").unwrap(), redis_url);
    assert!(redis_url.contains("corn_dce_test_redis"), "do not use production Redis");
    let mut conn = redis::Client::open(redis_url).unwrap().get_multiplexed_async_connection().await.unwrap();
    let key = format!("test:dce:ack:{}", uuid::Uuid::new_v4());
    let history = start_run(&db, &adapter.id).await.unwrap();
    let id = history.id.clone();
    let mut invalid = fixture("C2701"); invalid.value = -1.0;
    let update = serde_json::json!({"namespace":"dce","kind":"date","key":key,"value":"2026-10-21"});
    assert!(complete_run(db.clone(), adapter.clone(), history, true, Ok(CollectorBatch {
        records: vec![invalid], cursor_updates: vec![update.clone()],
    })).await.is_err());
    let value: Option<String> = redis::cmd("GET").arg(&key).query_async(&mut conn).await.unwrap();
    assert!(value.is_none());
    let history = run::Entity::find_by_id(id).one(&db).await.unwrap().unwrap();
    assert_eq!(history.status.as_deref(), Some("failed"));
    assert_eq!(history.failed_records, Some(1));
    assert!(history.error_message.unwrap().contains("1 records failed"));
    let run = start_run(&db, &adapter.id).await.unwrap();
    complete_run(db.clone(), adapter.clone(), run, true, Ok(CollectorBatch {
        records: vec![fixture("C2701")], cursor_updates: vec![update],
    })).await.unwrap();
    let value: String = redis::cmd("GET").arg(&key).query_async(&mut conn).await.unwrap();
    assert_eq!(value, "2026-10-21");
    let _: i32 = redis::cmd("DEL").arg(&key).query_async(&mut conn).await.unwrap();
}

#[tokio::test]
#[ignore = "requires an ephemeral TEST_DCE_DATABASE_URL"]
async fn source_failure_is_durable_and_recovery_closes_interrupted_runs() {
    let db = database().await;
    let adapter = dce(&db).await;
    let run = start_run(&db, &adapter.id).await.unwrap();
    let id = run.id.clone();
    assert!(complete_run(db.clone(), adapter.clone(), run, true,
        Err("HTTP 412 access denied".into())).await.unwrap_err().contains("412"));
    let failed = run::Entity::find_by_id(id).one(&db).await.unwrap().unwrap();
    assert_eq!(failed.status.as_deref(), Some("failed"));
    assert_eq!(failed.records_collected, 0);
    assert_eq!(failed.error_message.as_deref(), Some("HTTP 412 access denied"));
    start_run(&db, &adapter.id).await.unwrap();
    recover_interrupted_runs(&db).await.unwrap();
    let running = run::Entity::find().filter(run::Column::Status.eq("running")).count(&db).await.unwrap();
    assert_eq!(running, 0);
    let adapter = dce(&db).await;
    assert_eq!((adapter.total_runs, adapter.successful_runs, adapter.failed_runs), (2, 0, 2));
    let result = db.query_one(Statement::from_string(DbBackend::Postgres,
        "SELECT COUNT(*) AS n FROM raw_collection_records".to_string())).await.unwrap().unwrap();
    assert_eq!(result.try_get::<i64>("", "n").unwrap(), 0);
}
