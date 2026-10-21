//! Database module - SeaORM entity definitions

use sea_orm::entity::prelude::*;
use serde::{Deserialize, Serialize};

/// Raw collection records entity
#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
#[sea_orm(table_name = "raw_collection_records")]
pub struct Model {
    #[sea_orm(primary_key, auto_increment = false)]
    pub id: Uuid,
    pub collector_id: String,
    pub business_date: Date,
    pub indicator_name: String,
    pub value: Decimal,
    pub unit: String,
    pub region: Option<String>,
    pub source_url: String,
    pub original_text: Option<String>,
    pub dedup_key: String,
    pub collected_at: DateTimeWithTimeZone,
    pub created_at: Option<DateTimeWithTimeZone>,
    pub updated_at: Option<DateTimeWithTimeZone>,
}

#[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
pub enum Relation {}

impl ActiveModelBehavior for ActiveModel {}
