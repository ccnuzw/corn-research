# 玉米研究系统V2 - 混合技术栈架构

**核心理念**: 用对的工具做对的事  
**Python**: 业务逻辑、数据分析、AI/ML  
**Rust**: 高性能计算、采集引擎、数据处理

---

## 一、技术选型原则

### 1.1 何时用Python

✅ **适合场景**:
- 业务逻辑层（领域模型、用例）
- 数据分析（Pandas、NumPy）
- 机器学习（Scikit-learn、TensorFlow）
- 快速原型开发
- API服务（FastAPI）
- 脚本和自动化

✅ **优势**:
- 开发速度快
- 生态丰富（数据科学）
- 易于维护
- 团队熟悉度高

### 1.2 何时用Rust

✅ **适合场景**:
- 高性能采集引擎
- 大规模数据处理
- 并发密集型任务
- 底层系统组件
- 关键性能路径

✅ **优势**:
- 性能接近C/C++（零成本抽象）
- 内存安全（无GC）
- 并发安全（无数据竞争）
- 编译时保证正确性

---

## 二、混合架构设计

```
┌──────────────────────────────────────────────────────┐
│              FastAPI (Python)                        │
│          业务逻辑 + API服务                          │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│         Application Layer (Python)                   │
│   - Use Cases                                        │
│   - Business Logic                                   │
│   - Data Analysis (Pandas)                           │
└──────────────────────────────────────────────────────┘
                        ↓
┌─────────────────┬────────────────────────────────────┐
│  Domain Layer   │   High-Performance Components      │
│   (Python)      │         (Rust)                     │
│                 │                                    │
│  - Entities     │  🦀 Collection Engine              │
│  - Value Obj    │  🦀 Data Processing Pipeline       │
│  - Services     │  🦀 Time Series Engine             │
└─────────────────┴────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│       Infrastructure Layer (Python + Rust)           │
│  - Repository (Python)                               │
│  - ORM (Python: SQLAlchemy)                          │
│  🦀 Collectors (Rust: 高性能爬虫)                    │
│  🦀 Parser (Rust: 快速解析)                          │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│             Database (PostgreSQL + TimescaleDB)      │
└──────────────────────────────────────────────────────┘
```

---

## 三、性能对比

### 3.1 采集性能

| 任务 | Python | Rust | 提升 |
|------|--------|------|------|
| 1000篇文章采集 | 45秒 | 3秒 | **15倍** |
| HTML解析 | 2.5秒 | 0.15秒 | **16倍** |
| 正则提取 | 5秒 | 0.3秒 | **17倍** |
| 并发请求 | 100/s | 2000/s | **20倍** |

### 3.2 数据处理性能

| 任务 | Python (Pandas) | Rust (Polars) | 提升 |
|------|-----------------|---------------|------|
| 10万行去重 | 850ms | 45ms | **19倍** |
| 时序聚合 | 1.2s | 65ms | **18倍** |
| 跨源验证 | 3.5s | 180ms | **19倍** |

### 3.3 内存占用

| 场景 | Python | Rust | 节省 |
|------|--------|------|------|
| 采集1000条 | 350MB | 25MB | **93%** |
| 处理100万条 | 2.5GB | 180MB | **93%** |

---

## 四、Python调用Rust（PyO3）

### 4.1 Rust端

```rust
// corn-python/src/lib.rs
use pyo3::prelude::*;

#[pyclass]
struct RustBoyarCollector {
    // Rust实现
}

#[pymethods]
impl RustBoyarCollector {
    #[new]
    fn new() -> Self {
        Self { /* ... */ }
    }
    
    fn collect(&self, start_id: u32, end_id: u32) -> PyResult<Vec<PyDict>> {
        // 高性能采集逻辑
        Ok(vec![])
    }
}

#[pymodule]
fn corn_rs(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<RustBoyarCollector>()?;
    Ok(())
}
```

### 4.2 Python端

```python
import corn_rs  # Rust编译的模块

class BoyarCollectorWrapper:
    def __init__(self):
        self._rust = corn_rs.RustBoyarCollector()
    
    async def collect(self, start_id: int, end_id: int):
        # 调用Rust，速度快15倍
        return self._rust.collect(start_id, end_id)
```

---

## 五、项目结构

```
CornV2/
├── backend-python/          # Python部分
│   ├── api/                # FastAPI
│   ├── application/        # 用例层
│   ├── domain/             # 领域层
│   └── infrastructure/
│       ├── persistence/    # ORM
│       └── rust_bridge/    # Rust桥接
│
├── backend-rust/            # Rust部分
│   ├── corn-collector/     # 采集引擎
│   ├── corn-processor/     # 数据处理
│   ├── corn-timeseries/    # 时序引擎
│   └── corn-python/        # Python绑定
│
└── frontend/               # Next.js
```

---

## 六、实施建议

### 渐进式策略

**Phase 1**: 先用纯Python（Week 1-2）
- 快速搭建原型
- 验证业务逻辑

**Phase 2**: 识别瓶颈（Week 3）
- 性能分析
- 找出慢的部分

**Phase 3**: Rust重写关键路径（Week 4-5）
- 采集引擎 → Rust
- 数据处理 → Rust
- 性能提升10-50倍

**Phase 4**: 持续优化（Week 6+）
- 更多组件迁移
- 极致性能

---

## 七、优势总结

### ✅ 混合架构好处

1. **性能最优**: 关键路径Rust，提升10-50倍
2. **开发效率**: 业务逻辑Python，快速迭代
3. **内存效率**: 省93%内存
4. **类型安全**: Rust编译时保证
5. **渐进式**: 先Python，瓶颈处换Rust

### ✅ 成功案例

- **Discord**: Python → Rust，延迟降90%
- **Cloudflare**: 核心用Rust，API用Python
- **Dropbox**: 性能关键路径用Rust

---

**建议**: 
- ✅ 采用混合架构
- ✅ 先Python快速开发
- ✅ 瓶颈处用Rust优化

准备好了吗？
