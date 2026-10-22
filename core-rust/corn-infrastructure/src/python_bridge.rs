use pyo3::prelude::*;
pub use crate::raw_record::RawRecord;

pub struct PyO3Bridge;

impl PyO3Bridge {
    pub fn new() -> Self {
        Self
    }
    
    /// 调用Python采集器
    pub fn collect(&self, collector_id: &str) -> Result<Vec<RawRecord>, PyErr> {
        Python::with_gil(|py| {
            // 添加Python路径
            let sys = py.import_bound("sys")?;
            let path = sys.getattr("path")?;
            
            // 添加collectors-python目录
            let cwd = std::env::current_dir()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to get current dir: {}", e)
                ))?;
            
            let collectors_path = cwd.join("collectors-python");
            path.call_method1("insert", (0, collectors_path.to_str().unwrap()))?;
            
            // 导入采集器模块
            let collectors_module = py.import_bound("collectors")?;
            
            // 根据collector_id获取对应的类
            let collector_class = match collector_id {
                "boyar_shandong_v2" => {
                    collectors_module.getattr("BoyarCollectorV2")?
                }
                "sina_north_port" => {
                    collectors_module.getattr("SinaCollectorV2")?
                }
                "mock_test" => {
                    collectors_module.getattr("MockCollector")?
                }
                _ => {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Unknown collector: {}", collector_id)
                    ));
                }
            };
            
            // 实例化采集器
            let collector = collector_class.call0()?;
            
            // 调用collect方法
            let py_records = collector.call_method0("collect")?;
            
            // 转换为Rust结构
            self.convert_records(&py_records)
        })
    }
    
    fn convert_records(&self, py_records: &Bound<'_, PyAny>) -> Result<Vec<RawRecord>, PyErr> {
        let mut records = Vec::new();
        
        // 遍历Python返回的列表
        for item in py_records.iter()? {
            let record = self.convert_single_record(&item?)?;
            records.push(record);
        }
        
        Ok(records)
    }
    
    fn convert_single_record(&self, py_record: &Bound<'_, PyAny>) -> Result<RawRecord, PyErr> {
        // 提取字段
        let business_date: String = py_record
            .getattr("business_date")?
            .extract()?;
        
        // 提取collected_at（DateTime对象转字符串）
        let collected_at_obj = py_record.getattr("collected_at")?;
        let collected_at: String = collected_at_obj
            .call_method0("isoformat")?
            .extract()?;
        
        // 提取metadata中的collector_id
        let metadata = py_record.getattr("metadata")?;
        let collector_id: String = metadata
            .get_item("collector_id")?
            .extract()?;
        
        Ok(RawRecord {
            business_date,
            indicator_name: py_record.getattr("indicator")?.extract()?,
            value: py_record.getattr("value")?.extract()?,
            unit: py_record.getattr("unit")?.extract()?,
            region: py_record.getattr("region")?.extract()?,
            source_url: py_record.getattr("source_url")?.extract()?,
            original_text: py_record.getattr("original_text")?.extract()?,
            collector_id,
            collected_at,
        })
    }
}

impl Default for PyO3Bridge {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_python_bridge_mock() {
        let bridge = PyO3Bridge::new();
        let result = bridge.collect("mock_test");
        
        match result {
            Ok(records) => {
                assert!(!records.is_empty(), "应该采集到数据");
                println!("✓ 采集到 {} 条记录", records.len());
                
                // 验证第一条记录
                let first = &records[0];
                assert!(!first.indicator_name.is_empty());
                assert!(!first.unit.is_empty());
                
                println!("✓ 第一条记录: {} = {} {}", 
                    first.indicator_name, first.value, first.unit);
            }
            Err(e) => {
                panic!("采集失败: {:?}", e);
            }
        }
    }
}
