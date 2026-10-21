//! 统一错误处理
//!
//! 定义应用中所有可能的错误类型

use thiserror::Error;

#[derive(Error, Debug)]
pub enum CornError {
    #[error("Python error: {0}")]
    Python(String),
    
    #[error("Validation error: {0}")]
    Validation(String),
    
    #[error("Not found: {0}")]
    NotFound(String),
    
    #[error("Configuration error: {0}")]
    Config(String),
    
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
    
    #[error("Internal error: {0}")]
    Internal(String),
}

/// 统一的Result类型
pub type Result<T> = std::result::Result<T, CornError>;

impl axum::response::IntoResponse for CornError {
    fn into_response(self) -> axum::response::Response {
        use axum::http::StatusCode;
        use axum::Json;
        use serde_json::json;
        
        let (status, message) = match self {
            CornError::NotFound(msg) => (StatusCode::NOT_FOUND, msg),
            CornError::Validation(msg) => (StatusCode::BAD_REQUEST, msg),
            CornError::Config(msg) => (StatusCode::INTERNAL_SERVER_ERROR, msg),
            _ => (StatusCode::INTERNAL_SERVER_ERROR, self.to_string()),
        };
        
        let body = Json(json!({
            "success": false,
            "error": message,
        }));
        
        (status, body).into_response()
    }
}
