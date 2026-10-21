# Python + Rust 并行开发实施计划

**策略**: 从第一天开始就同时开发Python和Rust  
**目标**: 一次性构建高性能系统  
**周期**: 8周

---

## Week 1: 双轨启动

### Python轨道（3人日）

**Day 1-2: FastAPI基础**
```bash
# 创建Python项目结构
cd /Users/apple/CornV2/backend-python
mkdir -p app/{api,application,domain,infrastructure,config}

# 核心文件
- app/main.py              # FastAPI入口
- app/config/settings.py   # 配置
- app/api/dependencies.py  # DI容器
```

**Day 3: 数据模型定义**
```python
# domain/market_data/entities/price.py
# domain/market_data/value_objects/quality_score.py
# application/dtos/price_dto.py
```

### Rust轨道（4人日）

**Day 1-3: Rust项目初始化**
```bash
cd /Users/apple/CornV2/backend-rust

# 创建Workspace
cargo new --lib corn-collector
cargo new --lib corn-processor
cargo new --lib corn-python

# Cargo.toml (workspace)
[workspace]
members = ["corn-collector", "corn-processor", "corn-python"]
```

**Day 4-5: 采集引擎基础**
```rust
// corn-collector/src/lib.rs
pub mod engine;
pub mod collectors;
pub mod parser;

// corn-collector/src/engine/mod.rs
pub trait Collector {
    async fn collect(&self) -> Result<Vec<RawData>>;
}
```

**Day 6-7: Python绑定框架**
```rust
// corn-python/src/lib.rs
use pyo3::prelude::*;

#[pymodule]
fn corn_rs(_py: Python, m: &PyModule) -> PyResult<()> {
    // 绑定定义
    Ok(())
}
```

---

## Week 2: 核心组件开发

### Python轨道（基础设施）

**Day 1-3: 数据库层**
```python
# infrastructure/persistence/database.py
# infrastructure/persistence/models/
# infrastructure/persistence/repositories/
```

**Day 4-5: FastAPI端点**
```python
# api/v1/endpoints/prices.py
@router.get("/prices")
async def get_prices(...):
    pass
```

**Day 6-7: 依赖注入**
```python
# api/dependencies.py
container = Container()
container.wire(modules=[endpoints])
```

### Rust轨道（采集器实现）

**Day 1-4: 博亚和讯采集器**
```rust
// corn-collector/src/collectors/boyar.rs
pub struct BoyarCollector {
    client: reqwest::Client,
    base_url: String,
}

impl Collector for BoyarCollector {
    async fn collect(&self) -> Result<Vec<RawData>> {
        // 高性能并发采集
    }
}
```

**Day 5-7: HTML解析器**
```rust
// corn-collector/src/parser/html.rs
pub struct HtmlParser {
    patterns: Vec<Pattern>,
}

impl HtmlParser {
    pub fn extract(&self, html: &str) -> Vec<DataPoint> {
        // 零拷贝高性能解析
    }
}
```

---

## Week 3: 首个完整采集器

### Python轨道（用例层）

**Day 1-3: 采集用例**
```python
# application/use_cases/collection/run_collector.py
class RunCollectorUseCase:
    def __init__(self, rust_bridge: RustCollectorBridge):
        self._bridge = rust_bridge
    
    async def execute(self, request: RunCollectorRequest):
        # 调用Rust采集器
        return await self._bridge.collect(...)
```

**Day 4-5: Rust桥接层**
```python
# infrastructure/rust_bridge/collector_bridge.py
import corn_rs

class RustCollectorBridge:
    def __init__(self):
        self._boyar = corn_rs.BoyarCollector()
    
    async def collect_boyar(self, start_id, end_id):
        return self._boyar.collect(start_id, end_id)
```

### Rust轨道（完成博亚+开始新浪）

**Day 1-3: 博亚和讯完成**
- 完整实现
- 单元测试
- 性能测试

**Day 4-5: 新浪财经开始**
```rust
// corn-collector/src/collectors/sina.rs
pub struct SinaCollector {
    // 实现
}
```

**Day 6-7: Python绑定完成**
```rust
// corn-python/src/collectors.rs
#[pyclass]
pub struct PyBoyarCollector {
    inner: BoyarCollector,
}

#[pymethods]
impl PyBoyarCollector {
    #[new]
    fn new() -> Self { /* ... */ }
    
    fn collect(&self, start: u32, end: u32) -> PyResult<Vec<PyDict>> {
        // FFI调用
    }
}
```

---

## Week 4: 多采集器 + 数据处理

### Python轨道（业务逻辑）

**Day 1-2: 领域服务**
```python
# domain/validation/services/cross_source_validator.py
class CrossSourceValidator:
    def validate(self, records: List[RawData]) -> ValidationResult:
        # 多源验证逻辑
        pass
```

**Day 3-5: API完善**
```python
# 完整CRUD端点
# WebSocket实时推送
# 健康检查
```

### Rust轨道（数据处理引擎）

**Day 1-4: corn-processor开发**
```rust
// corn-processor/src/lib.rs
pub mod transform;
pub mod validation;
pub mod dedup;

// corn-processor/src/dedup/mod.rs
pub struct DedupEngine {
    // 高性能去重
}

impl DedupEngine {
    pub fn deduplicate(&self, data: Vec<RawData>) -> Vec<RawData> {
        // 使用HashSet + 并行处理
        // 比Python快20倍
    }
}
```

**Day 5-7: 新浪+DCE采集器**
```rust
// 完成新浪财经
// 开始DCE期货采集器
```

---

## Week 5: 性能优化 + 质量保障

### Python轨道（质量系统）

**Day 1-3: 异常检测**
```python
# domain/validation/services/anomaly_detector.py
# 时序异常检测（可选用Rust加速）
```

**Day 4-5: 审核界面API**
```python
# api/v1/endpoints/review.py
# 待审核数据CRUD
```

### Rust轨道（性能优化）

**Day 1-3: 时序引擎**
```rust
// corn-timeseries/src/lib.rs
pub struct TimeSeriesEngine {
    // 高性能时序查询
}
```

**Day 4-5: 性能调优**
- 并发优化
- 内存优化
- 缓存策略

**Day 6-7: 基准测试**
```rust
// benches/collector_bench.rs
#[bench]
fn bench_boyar_collect(b: &mut Bencher) {
    b.iter(|| {
        // 性能测试
    });
}
```

---

## Week 6: 前端 + 可视化

### Python轨道（API完善）

**Day 1-3: WebSocket实时推送**
```python
# api/websocket/realtime.py
@app.websocket("/ws/collector-monitor")
async def collector_monitor(websocket: WebSocket):
    # 实时推送采集进度
    pass
```

**Day 4-5: 数据导出API**
```python
# api/v1/endpoints/export.py
# CSV/Excel/PDF导出
```

### 前端轨道（7人日）

**Day 1-2: Next.js基础**
```typescript
// src/app/layout.tsx
// src/lib/api.ts
// 主题系统实现
```

**Day 3-5: 监控界面**
```typescript
// src/app/monitor/page.tsx
// 实时KPI
// 采集器状态
// 日志流
```

**Day 6-7: 数据浏览**
```typescript
// src/app/data/page.tsx
// 表格组件
// 溯源弹窗
```

---

## Week 7: 扩展数据源

### Rust轨道（新采集器）

**Day 1-3: 网易订阅**
```rust
// corn-collector/src/collectors/netease.rs
```

**Day 4-5: 国家统计局**
```rust
// corn-collector/src/collectors/nbs.rs
```

**Day 6-7: Mysteel（可选）**
```rust
// corn-collector/src/collectors/mysteel.rs
```

### Python轨道（集成）

**Day 1-7: 新采集器集成**
- Python绑定
- 用例实现
- API端点
- 前端展示

---

## Week 8: 优化与部署

### 全栈优化

**Day 1-2: 性能优化**
- Rust代码优化
- Python异步优化
- 数据库查询优化
- 前端打包优化

**Day 3-4: 部署准备**
```dockerfile
# Dockerfile.rust
FROM rust:1.75 as builder
WORKDIR /app
COPY backend-rust/ .
RUN cargo build --release

# Dockerfile.python
FROM python:3.11
COPY --from=rust-builder /app/target/release/*.so /app/lib/
COPY backend-python/ .
RUN pip install -r requirements.txt
```

**Day 5-7: 测试与文档**
- 端到端测试
- 性能基准报告
- API文档
- 部署手册

---

## 并行开发关键点

### 1. 团队分工

**Rust开发者**（关键）:
- 采集引擎
- 数据处理
- 性能优化

**Python开发者**:
- 业务逻辑
- API服务
- 数据分析

**全栈开发者**:
- 前端界面
- Python-Rust集成
- 部署运维

### 2. 接口定义（第一周确定）

```rust
// 定义清晰的FFI接口
#[pyclass]
pub struct CollectionResult {
    #[pyo3(get)]
    pub records: Vec<PyDict>,
    
    #[pyo3(get)]
    pub success_count: usize,
    
    #[pyo3(get)]
    pub duration_ms: u64,
}
```

### 3. 开发流程

```
Week 1:
Rust → 定义接口
Python → 定义模型

Week 2-3:
Rust → 实现采集器
Python → 实现用例（先mock Rust）

Week 4:
集成 → Python调用Rust

Week 5-8:
并行 → 各自优化
```

### 4. 测试策略

**Rust端**:
```rust
#[cfg(test)]
mod tests {
    #[tokio::test]
    async fn test_boyar_collector() {
        // 单元测试
    }
}
```

**Python端**:
```python
@pytest.mark.asyncio
async def test_run_collector_use_case():
    # 集成测试（使用真实Rust模块）
    pass
```

---

## 构建脚本

```bash
#!/bin/bash
# build.sh - 一键构建Python + Rust

echo "🦀 Building Rust components..."
cd backend-rust
cargo build --release

echo "🐍 Building Python bindings..."
cd corn-python
maturin develop --release

echo "🐍 Installing Python dependencies..."
cd ../../backend-python
pip install -r requirements.txt

echo "✅ Build complete!"
echo "📦 Rust libraries: backend-rust/target/release/"
echo "🐍 Python module: import corn_rs"
```

---

## 成功指标

### Week 4检查点
- [ ] Rust博亚和讯采集器工作
- [ ] Python成功调用Rust
- [ ] 性能达到目标（15倍提升）

### Week 6检查点
- [ ] 4个核心采集器完成（Rust）
- [ ] 前端监控界面可用
- [ ] 数据实时写入数据库

### Week 8检查点
- [ ] 系统完整运行
- [ ] 性能测试通过
- [ ] 文档齐全

---

**准备好了吗？立即开始Week 1 Day 1！** 🚀
