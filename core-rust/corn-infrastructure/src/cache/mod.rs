//! 缓存模块
//! 
//! 提供Redis缓存抽象和实现

mod redis_client;

pub use redis_client::RedisCache;
