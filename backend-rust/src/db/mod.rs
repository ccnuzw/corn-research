//! Database connection and utilities

pub mod entities;

use sea_orm::{Database, DatabaseConnection, DbErr};

/// Initialize database connection pool
pub async fn connect(database_url: &str) -> Result<DatabaseConnection, DbErr> {
    Database::connect(database_url).await
}
