//! 地区值对象

/// 地区值对象
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Location {
    name: String,
}

impl Location {
    pub fn new(name: String) -> Self {
        Self { name }
    }
    
    pub fn name(&self) -> &str {
        &self.name
    }
}
