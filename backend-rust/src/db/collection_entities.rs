//! Collection Management System - SeaORM Entities

use sea_orm::entity::prelude::*;
use serde::{Deserialize, Serialize};

/// 数据源实体
#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
#[sea_orm(table_name = "sources")]
pub struct Model {
    #[sea_orm(primary_key, auto_increment = false)]
    pub id: String,
    pub name: String,
    pub domain: Option<String>,
    pub description: Option<String>,
    pub status: String,
    pub created_at: Option<DateTimeWithTimeZone>,
    pub updated_at: Option<DateTimeWithTimeZone>,
}

#[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
pub enum Relation {
    #[sea_orm(has_many = "adapter::Entity")]
    Adapters,
}

impl Related<adapter::Entity> for Entity {
    fn to() -> RelationDef {
        Relation::Adapters.def()
    }
}

impl ActiveModelBehavior for ActiveModel {}

/// 采集适配器实体
pub mod adapter {
    use super::*;

    #[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
    #[sea_orm(table_name = "adapters")]
    pub struct Model {
        #[sea_orm(primary_key, auto_increment = false)]
        pub id: String,
        pub name: String,
        pub script_file: String,
        pub source_id: String,
        pub topic_name: String,
        pub status: String,
        pub last_run_at: Option<DateTimeWithTimeZone>,
        pub last_cursor: Option<String>,
        pub total_runs: i32,
        pub successful_runs: i32,
        pub failed_runs: i32,
        pub last_error: Option<String>,
        pub created_at: Option<DateTimeWithTimeZone>,
        pub updated_at: Option<DateTimeWithTimeZone>,
    }

    #[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
    pub enum Relation {
        #[sea_orm(
            belongs_to = "super::Entity",
            from = "Column::SourceId",
            to = "super::Column::Id"
        )]
        Source,
        #[sea_orm(has_many = "super::record::Entity")]
        Records,
        #[sea_orm(has_many = "super::run::Entity")]
        Runs,
    }

    impl Related<super::Entity> for Entity {
        fn to() -> RelationDef {
            Relation::Source.def()
        }
    }

    impl Related<super::record::Entity> for Entity {
        fn to() -> RelationDef {
            Relation::Records.def()
        }
    }

    impl Related<super::run::Entity> for Entity {
        fn to() -> RelationDef {
            Relation::Runs.def()
        }
    }

    impl ActiveModelBehavior for ActiveModel {}
}

/// 采集记录实体
pub mod record {
    use super::*;

    #[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
    #[sea_orm(table_name = "collection_records")]
    pub struct Model {
        #[sea_orm(primary_key, auto_increment = false)]
        pub id: String,
        pub adapter_id: String,
        pub business_date: Date,
        pub value: Option<Decimal>,
        pub unit: Option<String>,
        pub topic_name: Option<String>,
        pub record_key: String,
        pub indicator: Option<String>,
        pub region: Option<String>,
        pub metadata: Option<Json>,
        pub source_url: Option<String>,
        pub source_html_path: Option<String>,
        pub quality_grade: Option<String>,
        pub quality_score: Option<i32>,
        pub collected_at: DateTimeWithTimeZone,
        pub created_at: Option<DateTimeWithTimeZone>,
    }

    #[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
    pub enum Relation {
        #[sea_orm(
            belongs_to = "super::adapter::Entity",
            from = "Column::AdapterId",
            to = "super::adapter::Column::Id"
        )]
        Adapter,
    }

    impl Related<super::adapter::Entity> for Entity {
        fn to() -> RelationDef {
            Relation::Adapter.def()
        }
    }

    impl ActiveModelBehavior for ActiveModel {}
}

/// 采集运行历史实体
pub mod run {
    use super::*;

    #[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
    #[sea_orm(table_name = "collection_runs")]
    pub struct Model {
        #[sea_orm(primary_key, auto_increment = false)]
        pub id: String,
        pub adapter_id: String,
        pub started_at: DateTimeWithTimeZone,
        pub completed_at: Option<DateTimeWithTimeZone>,
        pub status: Option<String>,
        pub new_records: Option<i32>,
        pub duplicate_records: Option<i32>,
        pub failed_records: Option<i32>,
        pub start_cursor: Option<String>,
        pub end_cursor: Option<String>,
        pub error_message: Option<String>,
        pub records_collected: i32,
    }

    #[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
    pub enum Relation {
        #[sea_orm(
            belongs_to = "super::adapter::Entity",
            from = "Column::AdapterId",
            to = "super::adapter::Column::Id"
        )]
        Adapter,
    }

    impl Related<super::adapter::Entity> for Entity {
        fn to() -> RelationDef {
            Relation::Adapter.def()
        }
    }

    impl ActiveModelBehavior for ActiveModel {}
}
