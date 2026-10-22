//! Python绑定 - 数据处理服务
//!
//! 编译: maturin develop --release
//! 使用: import corn_rs

use pyo3::prelude::*;
use pyo3::types::PyDict;
use corn_domain::market_data::value_objects::QualityScore;
use corn_infrastructure::processing::{DeduplicationService, ValidationService, RawRecord};

/// 去重函数
#[pyfunction]
fn deduplicate_records(py: Python<'_>, records: Vec<Bound<'_, PyDict>>) -> PyResult<Vec<Py<PyDict>>> {
    // 转换Python dict为Rust结构
    let mut rust_records = Vec::new();
    
    for d in records {
        if let (Some(bd), Some(ind), Some(val), Some(reg), Some(url)) = (
            d.get_item("business_date")?,
            d.get_item("indicator")?,
            d.get_item("value")?,
            d.get_item("region")?,
            d.get_item("source_url")?,
        ) {
            if let (Ok(business_date), Ok(indicator), Ok(value), Ok(region), Ok(source_url)) = (
                bd.extract::<String>(),
                ind.extract::<String>(),
                val.extract::<f64>(),
                reg.extract::<String>(),
                url.extract::<String>(),
            ) {
                rust_records.push(RawRecord {
                    business_date,
                    indicator,
                    value,
                    region,
                    source_url,
                });
            }
        }
    }
    
    // Rust去重
    let deduped = DeduplicationService::deduplicate(rust_records);
    
    // 转换回Python dict
    let mut result = Vec::new();
    for r in deduped {
        let dict = PyDict::new_bound(py);
        dict.set_item("business_date", r.business_date)?;
        dict.set_item("indicator", r.indicator)?;
        dict.set_item("value", r.value)?;
        dict.set_item("region", r.region)?;
        dict.set_item("source_url", r.source_url)?;
        result.push(dict.unbind());
    }
    
    Ok(result)
}

/// 验证函数
#[pyfunction]
fn validate_records(py: Python<'_>, records: Vec<Bound<'_, PyDict>>) -> PyResult<Py<PyDict>> {
    // 转换
    let mut rust_records = Vec::new();
    
    for d in records {
        if let (Some(bd), Some(ind), Some(val), Some(reg), Some(url)) = (
            d.get_item("business_date")?,
            d.get_item("indicator")?,
            d.get_item("value")?,
            d.get_item("region")?,
            d.get_item("source_url")?,
        ) {
            if let (Ok(business_date), Ok(indicator), Ok(value), Ok(region), Ok(source_url)) = (
                bd.extract::<String>(),
                ind.extract::<String>(),
                val.extract::<f64>(),
                reg.extract::<String>(),
                url.extract::<String>(),
            ) {
                rust_records.push(RawRecord {
                    business_date,
                    indicator,
                    value,
                    region,
                    source_url,
                });
            }
        }
    }
    
    // Rust验证
    let result = ValidationService::validate(rust_records);
    
    // 返回结果
    let dict = PyDict::new_bound(py);
    dict.set_item("valid_count", result.valid.len())?;
    dict.set_item("invalid_count", result.invalid.len())?;
    
    Ok(dict.unbind())
}

/// Python调用的处理函数
#[pyfunction]
fn process_raw_data(records: Vec<Bound<'_, PyDict>>) -> PyResult<ProcessResult> {
    let mut processed = Vec::new();
    
    for record in records {
        // 从Python字典提取数据
        let value: f64 = record.get_item("value")?
            .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("value"))?.extract()?;
        let indicator: String = record.get_item("indicator")?
            .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("indicator"))?.extract()?;
        
        // Rust验证逻辑
        if value > 0.0 && value < 100000.0 {
            processed.push(indicator);
        }
    }
    
    Ok(ProcessResult {
        success: true,
        processed_count: processed.len(),
        message: "Processing complete".to_string(),
    })
}

/// 计算质量分数
#[pyfunction]
fn calculate_quality_score(
    source_tier: f64,
    completeness: f64,
    timeliness: f64,
) -> PyResult<f64> {
    let score = QualityScore::from_factors(source_tier, completeness, timeliness)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    
    Ok(score.value())
}

/// 处理结果
#[pyclass]
struct ProcessResult {
    #[pyo3(get)]
    success: bool,
    
    #[pyo3(get)]
    processed_count: usize,
    
    #[pyo3(get)]
    message: String,
}

/// Python模块定义
#[pymodule]
fn corn_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(deduplicate_records, m)?)?;
    m.add_function(wrap_pyfunction!(validate_records, m)?)?;
    m.add_function(wrap_pyfunction!(process_raw_data, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_quality_score, m)?)?;
    m.add_class::<ProcessResult>()?;
    Ok(())
}
