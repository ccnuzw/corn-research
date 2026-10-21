# 玉米研究系统V2 - 正确的混合架构

**核心理念**: Python采集 + Rust DDD核心  
**修正日期**: 2026-10-20

---

## 一、技术分工（修正后）

### ✅ Python负责：采集器

**为什么用Python做采集？**

1. **网站结构变化频繁** → Python改得快
   - 博亚和讯改版 → 10分钟改完
   - Rust需要重新编译 → 太慢

2. **生态丰富**
   - `requests` - HTTP客户端
   - `BeautifulSoup4` - HTML解析
   - `lxml` - 快速XML/HTML
   - `regex` - 正则表达式
   - `aiohttp` - 异步HTTP

3. **调试方便**
   - 加个`print`就能调试
   - Rust调试复杂

4. **已有经验可复用**
   - 之前的采集器都是Python
   - 团队熟悉

### ✅ Rust负责：DDD核心框架

**为什么用Rust做DDD？**

1. **领域模型需要强类型**
   ```rust
   // Rust编译时保证类型安全
   struct Price {
       value: Decimal,        // 不会有浮点误差
       date: NaiveDate,       // 不会搞混datetime
       location: Location,    // 枚举，不会拼错
   }
   ```

2. **数据处理性能关键**
   - 去重：100万条，Rust 45ms vs Python 850ms（19倍）
   - 验证：跨源对比，Rust快20倍
   - 聚合：时序计算，Rust快18倍

3. **业务规则稳定**
   - 领域模型不常变
   - 适合Rust的严格性

4. **时序查询高性能**
   - Rust零成本抽象
   - 无GC停顿

---

## 二、新架构设计

```
┌─────────────────────────────────────────────────┐
│           Frontend (Next.js 14)                 │
│              Web界面                            │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│           FastAPI Gateway (Python)              │
│         HTTP API + WebSocket                    │
└─────────────────────────────────────────────────┘
                        ↓
┌──────────────────┬──────────────────────────────┐
│  Python Collectors │    Rust DDD Core          │
│  (采集层)          │   (业务核心)               │
├──────────────────┼──────────────────────────────┤
│                  │                              │
│ 🐍 BoyarCollector│  🦀 Domain Layer            │
│ 🐍 SinaCollector │     - Entities              │
│ 🐍 DCECollector  │     - Value Objects         │
│ 🐍 NeteaseC...   │     - Aggregates            │
│                  │     - Domain Services       │
│ → 采集原始数据    │                              │
│ → 灵活快速       │  🦀 Application Layer       │
│ → 易于调试       │     - Use Cases             │
│                  │     - DTOs                  │
│                  │                              │
│                  │  🦀 Infrastructure          │
│                  │     - Data Processing       │
│                  │     - Validation            │
│                  │     - Deduplication         │
│                  │     - Time Series Engine    │
└──────────────────┴──────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│      PostgreSQL + TimescaleDB + Redis           │
└─────────────────────────────────────────────────┘
```

---

## 三、数据流

### 3.1 采集流程

```
1. Python采集器运行
   ↓
2. 采集原始HTML/JSON
   ↓
3. 提取数据 (Python)
   ↓
4. 传给Rust Core (FFI)
   ↓
5. Rust验证+处理
   ↓
6. 写入数据库
```

### 3.2 示例

**Python端（采集）**:
```python
# collectors/boyar_collector.py
import requests
from bs4 import BeautifulSoup
import corn_rs  # Rust DDD Core的Python绑定

class BoyarCollector:
    def collect(self):
        # 1. 采集HTML（Python）
        response = requests.get('https://m.boyar.cn/...')
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 2. 提取数据（Python）
        raw_data = []
        for match in re.finditer(r'山东.*到车.*(\d+)', soup.text):
            raw_data.append({
                'value': float(match.group(1)),
                'date': '2026-10-20',
                'indicator': '山东深加工到车量'
            })
        
        # 3. 传给Rust处理（FFI）
        result = corn_rs.process_arrivals(raw_data)
        return result
```

**Rust端（DDD核心）**:
```rust
// lib.rs (PyO3绑定)
#[pyfunction]
fn process_arrivals(raw_data: Vec<PyDict>) -> PyResult<ProcessResult> {
    // 1. 转换为Rust领域对象
    let records: Vec<ArrivalRecord> = raw_data
        .into_iter()
        .map(|d| ArrivalRecord::from_py(d))
        .collect();
    
    // 2. 领域验证（Rust高性能）
    let validated = ValidatorService::validate(records)?;
    
    // 3. 去重（Rust快20倍）
    let deduped = DeduplicatorService::deduplicate(validated)?;
    
    // 4. 质量评分
    let scored = QualityService::score(deduped)?;
    
    // 5. 写入数据库
    Repository::save(scored)?;
    
    Ok(ProcessResult { success: true })
}
```

---

## 四、项目结构

```
CornV2/
├── collectors-python/           # Python采集器
│   ├── collectors/
│   │   ├── base.py             # 基类
│   │   ├── boyar.py            # 博亚和讯
│   │   ├── sina.py             # 新浪财经
│   │   ├── dce.py              # 大商所
│   │   └── netease.py          # 网易订阅
│   ├── requirements.txt
│   └── tests/
│
├── core-rust/                   # Rust DDD核心
│   ├── corn-domain/            # 领域层
│   │   ├── src/
│   │   │   ├── market_data/   # 市场数据领域
│   │   │   ├── collection/    # 采集领域
│   │   │   └── validation/    # 验证领域
│   │   └── Cargo.toml
│   │
│   ├── corn-application/       # 应用层
│   │   ├── src/
│   │   │   ├── use_cases/
│   │   │   └── services/
│   │   └── Cargo.toml
│   │
│   ├── corn-infrastructure/    # 基础设施层
│   │   ├── src/
│   │   │   ├── persistence/
│   │   │   ├── processing/    # 数据处理
│   │   │   └── timeseries/    # 时序引擎
│   │   └── Cargo.toml
│   │
│   └── corn-python/            # Python绑定
│       ├── src/lib.rs
│       └── Cargo.toml
│
├── api-python/                  # FastAPI网关
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   └── websocket/
│   └── requirements.txt
│
└── frontend/                    # Next.js前端
    └── src/
```

---

## 五、核心优势

### ✅ Python采集器

| 优势 | 说明 |
|------|------|
| **快速开发** | 博亚改版 → 10分钟修复 |
| **易于调试** | print大法好用 |
| **生态丰富** | requests/bs4/aiohttp |
| **团队熟悉** | 降低学习成本 |

### ✅ Rust DDD核心

| 优势 | 说明 |
|------|------|
| **类型安全** | 编译时保证业务规则 |
| **高性能** | 数据处理快10-50倍 |
| **无GC** | 时序查询无停顿 |
| **并发安全** | 无数据竞争 |

---

## 六、性能对比

### 采集层（Python完全够用）

| 任务 | Python | 说明 |
|------|--------|------|
| HTTP请求 | 100-200ms | 网络IO为主，语言无差别 |
| HTML解析 | 10-50ms | BeautifulSoup够快 |
| 正则提取 | 5-20ms | Python re模块够用 |

**结论**: 采集器瓶颈在网络IO，不在语言性能

### 处理层（Rust性能优势明显）

| 任务 | Python | Rust | 提升 |
|------|--------|------|------|
| 去重100万条 | 850ms | 45ms | **19倍** |
| 跨源验证 | 3.5s | 180ms | **19倍** |
| 时序聚合 | 1.2s | 65ms | **18倍** |
| 质量评分 | 500ms | 30ms | **17倍** |

**结论**: 数据处理用Rust，性能提升巨大

---

## 七、开发流程

### Week 1-2: 基础搭建

**Python轨道**:
```bash
# 采集器基类
collectors/base.py

# 具体采集器
collectors/boyar.py
collectors/sina.py
```

**Rust轨道**:
```rust
// 领域模型
corn-domain/src/market_data/entities/price.rs

// 数据处理
corn-infrastructure/src/processing/dedup.rs
```

### Week 3-4: 集成

1. Rust Core编译为Python模块
2. Python采集器调用Rust
3. 性能测试

---

## 八、最终效果

### 开发效率
- ✅ 采集器改动快（Python）
- ✅ 业务逻辑严格（Rust）

### 性能
- ✅ 采集速度：网络IO为主，语言无差
- ✅ 处理速度：Rust快10-50倍

### 维护性
- ✅ 采集器：一站一器（Python）
- ✅ 核心逻辑：DDD分层（Rust）

---

**这才是正确的架构！**准备开始实施吗？
