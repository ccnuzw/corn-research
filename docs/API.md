# API文档

**版本**: v2.0.0-release  
**Base URL**: `http://localhost:18000/api`  
**认证**: 暂无（未来版本将添加JWT）

## 概述

玉米研究系统V2提供RESTful API，支持数据采集、查询、质量评估和系统监控等功能。所有响应均为JSON格式。

## 通用规范

### 响应格式

**成功响应**:
```json
{
  "status": "success",
  "data": { ... }
}
```

**错误响应**:
```json
{
  "status": "error",
  "message": "错误描述",
  "code": "ERROR_CODE"
}
```

### HTTP状态码

- `200 OK` - 请求成功
- `201 Created` - 资源创建成功
- `400 Bad Request` - 请求参数错误
- `404 Not Found` - 资源不存在
- `422 Unprocessable Entity` - 数据验证失败
- `500 Internal Server Error` - 服务器错误

### 分页参数

大多数列表端点支持分页：

- `limit` (可选): 每页记录数，默认10，最大100
- `offset` (可选): 跳过的记录数，默认0

## API端点

### 1. 健康检查

#### GET /health

检查系统健康状态。

**请求**:
```bash
curl http://localhost:18000/api/health
```

**响应**:
```json
{
  "status": "healthy",
  "timestamp": "2026-10-21T10:00:00Z",
  "version": "2.0.0",
  "services": {
    "database": "ok",
    "redis": "ok"
  }
}
```

---

### 2. 采集器管理

#### GET /collectors

列出所有可用的采集器。

**请求**:
```bash
curl http://localhost:18000/api/collectors
```

**响应**:
```json
[
  {
    "id": "boyar",
    "name": "博亚和讯采集器",
    "description": "采集博亚和讯玉米市场文章",
    "status": "active",
    "last_run": "2026-10-21T09:30:00Z",
    "total_records": 1250
  },
  {
    "id": "sina",
    "name": "新浪财经采集器",
    "description": "采集新浪财经期货行情",
    "status": "active",
    "last_run": "2026-10-21T09:35:00Z",
    "total_records": 890
  }
]
```

#### POST /collectors/run

同步运行指定采集器，等待 Python 采集完成后返回计数。完整路径为
`POST /api/collectors/run`。兼容入口 `POST /api/collectors/:id/run` 保留，路径入口无需请求体。

**请求**:
```bash
curl -X POST http://localhost:18000/api/collectors/run \
  -H "Content-Type: application/json" \
  -d '{
    "collector_name": "boyar_production",
    "max_items": 100
  }'
```

**请求体**:
```json
{
  "collector_name": "boyar_production",
  "max_items": 100
}
```

`collector_name` 必填，兼容旧字段名 `collector_id`，不能同时传两个字段。
可用名称：`boyar`、`boyar_production`、`sina`、`sina_production`、`mock`、`dce`、`cft`。
`max_items` 为可选正整数，默认 100，传给采集器作为数量提示；实际数量取决于采集器实现。
空名称、未知名称或 `max_items=0` 返回 400；缺失必填字段/字段类型错误返回 422；Python 执行失败返回 500。

**HTTP 200 响应示例**（数量仅示例）:
```json
{
  "success": true,
  "data": {
    "collector_id": "boyar_production",
    "records_collected": 1
  },
  "message": "Collected 1 records"
}
```

此入口沿用旧运行接口语义，**不保存采集结果到数据库**；需要异步运行、入库和运行历史时，
使用 `POST /api/adapters/:id/run`，并轮询 `GET /api/adapters/:id/runs`。
返回的 `success=true` 不代表数据已入库或数据质量验收通过。

运行历史补充：两种 collector 入口也会在 `collection_runs` 写入历史，并在响应 `data` 中
返回 `run_id`。要求采集脚本唯一对应一个已配置适配器；无对应或存在多个对应时返回 400，
应改用明确指定适配器的运行入口。`boyar` / `sina` 分别映射到其 production 脚本。
`records_collected` 表示抓取数量，`new_records` 表示实际新入库数量，两者不得混用。

#### GET /adapters/:id/runs

完整路径：`GET /api/adapters/:id/runs?limit=20&offset=0`。
从 `collection_runs` 查询，按 `started_at DESC, id DESC` 排序；仅返回该适配器历史。
`limit` 默认 20，范围 1–100；`offset` 默认 0。无历史的已有适配器返回空数组；
适配器不存在返回 404；无效分页参数返回 400。

```json
{
  "success": true,
  "data": [{
    "id": "example-run-id",
    "adapter_id": "adapter_boyar_arrivals",
    "started_at": "2026-10-22T04:00:00Z",
    "completed_at": "2026-10-22T04:00:10Z",
    "status": "success",
    "records_collected": 1,
    "new_records": 1,
    "duplicate_records": 0,
    "failed_records": 0,
    "start_cursor": null,
    "end_cursor": null,
    "error_message": null
  }],
  "message": null
}
```

状态为 `running`、`success`、`failed`；完成时写结束时间及错误原因，
有解析/入库失败的任务不会标为 success。适配器计数与历史结束状态在同一数据库事务中更新。
当前单后端 Compose 部署启动时，将遗留 running 历史标记为 failed（进程重启中断）；
多实例部署前须改为带 worker 所有权/心跳的恢复逻辑。
`GET /api/collectors/:id/history` 同样查询真实历史，不再返回固定空数组。

部署前执行幂等迁移：
```bash
docker exec -i corn_postgres psql -v ON_ERROR_STOP=1 -U corn_user -d corn_research \
  < migrations/006_collection_run_counts.sql
```

历史回归：`python3 backend-rust/tests/history_api.py`；创建的临时适配器及其记录自动删除，
对已有 mock 适配器发起的同步运行历史保留。

#### GET /collectors/:id/status

查询采集器运行状态。

**请求**:
```bash
curl http://localhost:18000/api/collectors/boyar/status
```

**响应**:
```json
{
  "collector_id": "boyar",
  "status": "idle",              // idle | running | error
  "current_job": null,
  "last_run": {
    "started_at": "2026-10-21T09:30:00Z",
    "completed_at": "2026-10-21T09:32:15Z",
    "records_collected": 15,
    "errors": 0
  },
  "statistics": {
    "total_runs": 120,
    "total_records": 1250,
    "success_rate": 0.98
  }
}
```

#### GET /collectors/:id/history

查询采集器运行历史。

**请求**:
```bash
curl http://localhost:18000/api/collectors/boyar/history?limit=10
```

**响应**:
```json
{
  "collector_id": "boyar",
  "items": [
    {
      "job_id": "job_123456",
      "started_at": "2026-10-21T09:30:00Z",
      "completed_at": "2026-10-21T09:32:15Z",
      "status": "completed",
      "records_collected": 15,
      "errors": 0
    }
  ],
  "total": 120,
  "limit": 10,
  "offset": 0
}
```

---

### 3. 数据查询

#### GET /data/latest

从 `raw_collection_records` 读取最新数据，完整路径为 `GET /api/data/latest`。
本节及采集运行接口以实际 `success/data/message` 响应为准，不使用旧示例中的 `status` 包装。

```bash
curl 'http://localhost:18000/api/data/latest?topic=shandong_arrivals&limit=10'
```

| 参数 | 语义 |
| --- | --- |
| `topic` | 可选；按下表转换成指标名，在 SQL 中过滤 |
| `indicator` | 可选；精确匹配指标名；与 `topic` 同传时取交集 |
| `days` | 可选；默认 30，仅查询今天及之前对应天数内的数据 |
| `limit` | 可选；默认 100；在过滤后限制数量 |

Topic 契约（P2-D001）：旧原始表没有 topic 字段，采用明确的兼容映射，禁止忽略未知 topic。

| Topic | 匹配 `indicator_name` |
| --- | --- |
| `shandong_arrivals`、`corn_arrivals` | `山东到车量`、`山东深加工到车量` |
| `corn_spot_price` | `玉米现货价格` |
| `north_port_inventory` | `北方四港库存` |
| `north_port_shipping` | `北方四港下海量` |
| 其他非别名值 | 将该值作为指标名精确匹配；不存在时返回空数组 |

不传 topic 保持原有查询；结果按业务日期、采集时间倒序排列。
此映射只属于 latest 接口，不改变适配器 topic 配置或 `/api/records` 的语义。

**HTTP 200 响应示例**:
```json
{
  "success": true,
  "data": [{
    "id": "2de03d6a-d1fd-49f3-9f73-4469ae213e3b",
    "business_date": "2026-10-08",
    "indicator_name": "山东深加工到车量",
    "value": 1027.0,
    "unit": "台",
    "source": "boyar_shandong_production",
    "quality": "A",
    "collected_at": "2026-10-21T05:56:24.662215Z"
  }],
  "message": null
}
```

注意：`quality` 仍为旧实现的固定值 `A`，不表示真实质量评分，本次不修改质量评估链路。

验收与回归：
- P2-AC01：给定可用采集器，调用两种运行入口均返回 HTTP 200 和采集计数；
  无效名称返回 400，不应返回路由 404。
- P2-AC02：给定混合指标数据，传山东到车 topic 仅返回两种山东指标；未知 topic 返回空数组；
  topic 与 indicator、日期和 limit 条件共同生效。
- 自动化资产：`backend-rust/src/handlers.rs` 的 `api_regression_tests`、
  `collectors-python/tests/test_runner_protocol.py`、`backend-rust/tests/api_regression.py`。
- 命令：`cargo test --locked --manifest-path backend-rust/Cargo.toml --bin corn-backend api_regression_tests`；
  `python3 -m unittest discover -s collectors-python/tests -v`；
  后端重启后运行 `python3 backend-rust/tests/api_regression.py`。

#### GET /data/raw

查询RAW层原始数据。

**请求**:
```bash
curl "http://localhost:18000/api/data/raw?limit=10&offset=0&collector_id=boyar"
```

**查询参数**:
- `limit` (可选): 每页记录数
- `offset` (可选): 偏移量
- `collector_id` (可选): 按采集器过滤
- `start_date` (可选): 起始日期 (YYYY-MM-DD)
- `end_date` (可选): 结束日期 (YYYY-MM-DD)

**响应**:
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "collector_id": "boyar",
      "source_url": "https://boyar.com/article/001",
      "collected_at": "2026-10-21T09:30:00Z",
      "raw_content": {
        "title": "山东玉米价格稳中有涨",
        "content": "...",
        "date": "2026-10-21"
      },
      "content_hash": "abc123...",
      "metadata": {
        "html_path": "data/raw/html/boyar/2026-10-21/001.html.gz"
      }
    }
  ],
  "total": 1250,
  "limit": 10,
  "offset": 0
}
```

#### GET /data/standard

查询STANDARD层标准化数据。

**请求**:
```bash
curl "http://localhost:18000/api/data/standard?limit=10&quality_grade=A,B"
```

**查询参数**:
- `limit`, `offset`: 分页
- `indicator` (可选): 指标名称
- `region` (可选): 地区
- `quality_grade` (可选): 质量等级 (A,B,C,D)，逗号分隔
- `start_date`, `end_date`: 日期范围

**响应**:
```json
{
  "items": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "business_date": "2026-10-21",
      "indicator_name": "山东玉米到车量",
      "value": 500.0,
      "unit": "台",
      "region": "山东",
      "quality_grade": "B",
      "quality_score": 85.0,
      "quality_issues": [],
      "source_id": "boyar",
      "raw_record_id": "550e8400-e29b-41d4-a716-446655440000",
      "collected_at": "2026-10-21T09:30:00Z",
      "standardized_at": "2026-10-21T09:31:00Z",
      "version": 1,
      "is_latest": true
    }
  ],
  "total": 890,
  "limit": 10,
  "offset": 0
}
```

#### GET /data/indicators

获取所有可用指标列表。

**请求**:
```bash
curl http://localhost:18000/api/data/indicators
```

**响应**:
```json
[
  {
    "name": "山东玉米到车量",
    "unit": "台",
    "category": "现货",
    "description": "山东地区玉米日到车量",
    "data_points": 150
  },
  {
    "name": "北方四港库存",
    "unit": "万吨",
    "category": "库存",
    "description": "北方四港玉米库存总量",
    "data_points": 200
  }
]
```

#### GET /data/:id/lineage

查询数据血统（追溯数据来源）。

**请求**:
```bash
curl http://localhost:18000/api/data/660e8400-e29b-41d4-a716-446655440000/lineage
```

**响应**:
```json
{
  "standard": {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "indicator_name": "山东玉米到车量",
    "value": 500.0,
    "quality_grade": "B",
    "standardized_at": "2026-10-21T09:31:00Z"
  },
  "raw": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "collector_id": "boyar",
    "source_url": "https://boyar.com/article/001",
    "collected_at": "2026-10-21T09:30:00Z"
  },
  "lineage": {
    "collector": "boyar",
    "original_url": "https://boyar.com/article/001",
    "collected_at": "2026-10-21T09:30:00Z",
    "standardized_at": "2026-10-21T09:31:00Z",
    "html_archive": "data/raw/html/boyar/2026-10-21/001.html.gz",
    "transformations": [
      "数据清洗",
      "格式标准化",
      "质量评估"
    ]
  }
}
```

#### POST /data/standardize

手动触发数据标准化（RAW → STANDARD）。

**请求**:
```bash
curl -X POST http://localhost:18000/api/data/standardize \
  -H "Content-Type: application/json" \
  -d '{
    "raw_record_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

**响应**:
```json
{
  "status": "success",
  "standard_record_id": "660e8400-e29b-41d4-a716-446655440000",
  "quality_grade": "B",
  "quality_score": 85.0
}
```

#### POST /data/auto-promote

自动晋升高质量数据（B级以上）。

**请求**:
```bash
curl -X POST http://localhost:18000/api/data/auto-promote \
  -H "Content-Type: application/json" \
  -d '{
    "min_quality_grade": "B",
    "limit": 100
  }'
```

**响应**:
```json
{
  "status": "success",
  "promoted_count": 25,
  "skipped_count": 5,
  "total_processed": 30
}
```

---

### 4. 质量评估

#### GET /quality/summary

获取质量评估汇总统计。

**请求**:
```bash
curl http://localhost:18000/api/quality/summary
```

**响应**:
```json
{
  "total_records": 890,
  "by_grade": {
    "A": 250,
    "B": 400,
    "C": 200,
    "D": 40
  },
  "average_score": 82.5,
  "data_sources": {
    "boyar": 600,
    "sina": 290
  },
  "last_updated": "2026-10-21T10:00:00Z"
}
```

#### GET /quality/grades

获取质量等级分布详情。

**请求**:
```bash
curl http://localhost:18000/api/quality/grades
```

**响应**:
```json
[
  {
    "grade": "A",
    "count": 250,
    "percentage": 28.1,
    "avg_score": 92.5,
    "description": "优秀"
  },
  {
    "grade": "B",
    "count": 400,
    "percentage": 44.9,
    "avg_score": 82.0,
    "description": "良好"
  },
  {
    "grade": "C",
    "count": 200,
    "percentage": 22.5,
    "avg_score": 72.0,
    "description": "及格"
  },
  {
    "grade": "D",
    "count": 40,
    "percentage": 4.5,
    "avg_score": 55.0,
    "description": "不合格"
  }
]
```

#### GET /quality/issues

获取质量问题列表。

**请求**:
```bash
curl "http://localhost:18000/api/quality/issues?severity=high"
```

**查询参数**:
- `severity` (可选): 严重程度 (high | medium | low)

**响应**:
```json
{
  "items": [
    {
      "record_id": "660e8400-e29b-41d4-a716-446655440000",
      "indicator": "山东玉米到车量",
      "severity": "medium",
      "issues": [
        "数据超过72小时",
        "缺少地区信息"
      ],
      "quality_score": 75.0,
      "detected_at": "2026-10-21T09:31:00Z"
    }
  ],
  "total": 120
}
```

---

### 5. 缓存管理

#### GET /cache/stats

获取缓存统计信息。

**请求**:
```bash
curl http://localhost:18000/api/cache/stats
```

**响应**:
```json
{
  "hit_rate": 0.85,
  "total_hits": 8500,
  "total_misses": 1500,
  "total_requests": 10000,
  "keys_count": 250,
  "memory_usage": "15.5 MB",
  "uptime_seconds": 86400
}
```

#### POST /cache/clear

清除所有缓存。

**请求**:
```bash
curl -X POST http://localhost:18000/api/cache/clear
```

**响应**:
```json
{
  "status": "success",
  "message": "缓存已清除",
  "keys_cleared": 250
}
```

#### DELETE /cache/:key

删除指定缓存键。

**请求**:
```bash
curl -X DELETE http://localhost:18000/api/cache/indicators:all
```

**响应**:
```json
{
  "status": "success",
  "message": "缓存键已删除",
  "key": "indicators:all"
}
```

---

### 6. 系统监控

#### GET /metrics

获取系统性能指标（Prometheus格式）。

**请求**:
```bash
curl http://localhost:18000/metrics
```

**响应**:
```
# HELP api_requests_total Total number of API requests
# TYPE api_requests_total counter
api_requests_total{method="GET",endpoint="/data/raw"} 5000

# HELP api_request_duration_seconds API request duration
# TYPE api_request_duration_seconds histogram
api_request_duration_seconds_bucket{le="0.1"} 4500
api_request_duration_seconds_bucket{le="0.2"} 4900
```

#### GET /stats

获取系统统计信息。

**请求**:
```bash
curl http://localhost:18000/api/stats
```

**响应**:
```json
{
  "database": {
    "raw_records": 1250,
    "standard_records": 890,
    "total_size": "125 MB"
  },
  "collectors": {
    "total": 2,
    "active": 2,
    "last_24h_runs": 48
  },
  "cache": {
    "hit_rate": 0.85,
    "keys": 250
  },
  "api": {
    "total_requests": 10000,
    "avg_response_time": 0.15
  }
}
```

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| `COLLECTOR_NOT_FOUND` | 采集器不存在 |
| `COLLECTOR_ALREADY_RUNNING` | 采集器正在运行 |
| `RECORD_NOT_FOUND` | 记录不存在 |
| `INVALID_PARAMETERS` | 参数验证失败 |
| `DATABASE_ERROR` | 数据库错误 |
| `CACHE_ERROR` | 缓存错误 |
| `STANDARDIZATION_FAILED` | 标准化失败 |

## 速率限制

当前版本暂无速率限制。未来版本将实现：
- 每IP每分钟最多100次请求
- 超出限制返回 `429 Too Many Requests`

## 认证

当前版本暂无认证。未来版本将支持：
- JWT Token认证
- API Key认证
- OAuth 2.0

## 示例代码

### Python

```python
import requests

# 运行采集器
response = requests.post(
    "http://localhost:18000/api/collectors/run",
    json={"collector_id": "boyar", "max_items": 10}
)
print(response.json())

# 查询数据
response = requests.get(
    "http://localhost:18000/api/data/standard",
    params={"limit": 10, "quality_grade": "A,B"}
)
data = response.json()
print(f"找到 {data['total']} 条记录")
```

### JavaScript

```javascript
// 运行采集器
const response = await fetch('http://localhost:18000/api/collectors/run', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ collector_id: 'boyar', max_items: 10 })
});
const result = await response.json();
console.log(result);

// 查询数据
const dataResponse = await fetch(
  'http://localhost:18000/api/data/standard?limit=10&quality_grade=A,B'
);
const data = await dataResponse.json();
console.log(`找到 ${data.total} 条记录`);
```

### cURL

```bash
# 运行采集器
curl -X POST http://localhost:18000/api/collectors/run \
  -H "Content-Type: application/json" \
  -d '{"collector_id":"boyar","max_items":10}'

# 查询数据
curl "http://localhost:18000/api/data/standard?limit=10&quality_grade=A,B"

# 查询血统
curl http://localhost:18000/api/data/660e8400-e29b-41d4-a716-446655440000/lineage
```

---

**更新日期**: 2026-10-21  
**维护者**: 玉米研究团队

## Day 3: Sina corn prices (Option A)

`SinaProductionCollector` now reads the real corn channel
`https://finance.sina.com.cn/money/future/C/`, discovers dated corn/soybean-meal
reports, and reads only their corn processor price table. It also reads Sina's
`https://hq.sinajs.cn/list=nf_C0` quote response with a Sina Referer header.
It does **not** provide north-port inventory/shipping and never substitutes mock data.

Apply `migrations/007_sina_corn_prices.sql` before deploying the new backend.
The existing `adapter_sina_spot` ID and `sina` / `sina_production` aliases stay valid.
For this collector, both `POST /api/collectors/run` and
`POST /api/adapters/adapter_sina_spot/run` persist records. Other legacy collector
calls retain their previous fetch-only behavior; adapter runs persist normally.

- Topics: `corn_spot_price`, `corn_futures_price`; both work with `/api/data/latest?topic=...`.
- Full provenance: `GET /api/adapters/adapter_sina_spot/records?limit=100` includes
  `indicator`, `region`, `record_key`, `metadata`, and `quality_grade=B`.
- Spot `region` denotes the enterprise/quote location label, not a normalized province.
  Moisture/quality labels are preserved, not normalized into a comparable national price.
- `nf_C0` is a continuous quotation, **not a deliverable contract**. Configure
  `SINA_FUTURES_SYMBOLS=nf_C0,nf_C2701` in the runner environment to include explicit
  contracts; validate contract availability before configuring production.
- Spot business dates come from report titles; futures dates/times come from the
  response fields. Publication date and collection date are not substituted.
- Deduplication is one **first daily snapshot** per adapter/date/topic/enterprise or symbol;
  repeats count as duplicates, not intraday tick updates. Inserts into collection and
  raw tables are atomic per observation, not across the entire batch.
- `/api/data/latest` remains a legacy projection: it omits per-series metadata and
  still hardcodes quality A. Use the adapter records endpoint for authoritative B
  quality and provenance until the legacy projection is corrected in Day 4.

## Day 3: Simplified Scheduler (Option A)

Apply `migrations/008_scheduler.sql` before deploying. Jobs and execution histories
are persisted in `scheduled_jobs` and `job_executions`; startup loads saved jobs.
Two seeded examples remain **disabled** pending Day 4 automatic-execution validation.
Manual triggers are deliberately allowed for disabled jobs.

| Job ID | Collector | Beijing Time | UTC Cron |
| --- | --- | --- | --- |
| `89000000-0000-4000-8000-000000000001` | `boyar_production` | 08:00 | `0 0 0 * * *` |
| `89000000-0000-4000-8000-000000000002` | `sina_production` | 09:00 | `0 0 1 * * *` |

All cron expressions use UTC and include seconds (six fields). API job objects
include `timezone: "UTC"`. Do not enter Beijing hour values as UTC hour values.

- `GET /api/scheduler/jobs`: durable configuration, state, counters and next run.
- `POST /api/scheduler/jobs`: name, collector_id, cron_expression, description?, enabled?.
- `POST /api/scheduler/jobs/:id`: real asynchronous manual collection, returns
  `{execution_id, status: "running"}`; overlapping execution of the same job is rejected.
- `GET /api/scheduler/jobs/:id/executions`: default limit20; limit1..100, offset>=0;
  optional `status=running|success|failed`, `start_date` and `end_date` (RFC3339 timestamps).
  Results sort by started_at DESC,id DESC and expose the underlying collection_run_id.
- `PUT /api/scheduler/jobs/:id/enable`: `{enabled: bool}`. Enabling automatic runs
  is intentionally deferred until Day 4 verification.
- `DELETE /api/scheduler/jobs/:id`: rejects running jobs; deletes job/history by cascade.
- General PUT editing remains unsupported (HTTP501); disable/delete and recreate instead.

This is a single-backend Compose deployment. Restart recovery marks interrupted
runs failed; missed schedules are not replayed. Automatic timing, catch-up behavior,
notification-failure handling and multi-instance lifecycle need Day 4 validation.

Manual-trigger quick reference:

```sh
# Sina example; substitute ...0001 for the Boyar example.
curl -fsS -X POST http://localhost:18000/api/scheduler/jobs/89000000-0000-4000-8000-000000000002
curl -fsS 'http://localhost:18000/api/scheduler/jobs/89000000-0000-4000-8000-000000000002/executions?limit=20&offset=0'
```

POST acceptance is not collection success: match its returned execution_id to a
history row and wait for success/failed. Failed executions contain error_message
and completed_at; the job exposes last_error and failed_count. An isolated real
runner failure and independent PostgreSQL persistence check passed via
`python3 backend-rust/tests/scheduler_failure.py`. This test cleans up its own
job/adapter and saves evidence under docs/reports; it does not alter either example.

## P1 Release Hardening

Sina HTTP requests rotate **desktop** User-Agent strings; mobile clients can receive
an unrelated CBOT application shell. Bounded real-source fallbacks, alternative
article containers/headers and detailed diagnostics replace the former fragile
single-selector behavior. No mock fallback is used. Source network retries can
exceed a30-second client timeout; wait for the linked collection-run status or use
an appropriately bounded client timeout (the live regression uses180seconds).

Latest-data queries now validate days1..36500 and limit1..10000; trend queries
validate days1..36500. Invalid ranges return HTTP400 rather than risking date
arithmetic panic. Critical startup failures log and exit1 instead of panicking;
API serialization failures return HTTP500.

## Phase 2: Async Collection Jobs

Apply `migrations/009_async_jobs.sql` before deploying the backend.

`POST /api/collectors/run/async` accepts
`{"collector_name":"boyar_production","max_items":100}` (collector_id alias supported).
Returns HTTP202, `{success:true,data:{job_id,status:"queued",status_url},message}`.
max_items must be1..1000; unknown/unmapped collector400, duplicate active adapter409.
The response is sent after the durable queue insert, not after collection finishes.

`GET /api/jobs/:id` returns an AsyncJob with status queued/running/succeeded/failed,
progress0..100, phase, phase-specific details, result.records_collected on success,
error_message on failure, run_id and timestamps. Unknown UUID404, malformed UUID400.
Poll until a terminal state. Async runs persist records and have normal collection
history. Existing synchronous and adapter endpoints keep their previous contracts.

Two workers process the queue. Progress reflects actual phase/work events; only
successful persistence/run finalization reaches100. Async Python is bounded to2h.
On single-backend restart, queued jobs resume; interrupted running jobs fail explicitly,
while jobs linked to already committed successful runs reconcile to succeeded.
There is no automatic replay/cancel endpoint or exactly-once Redis/SQL guarantee.
See `docs/reports/PHASE2_DAY1_TASK1.md` for tests and operational limits.

## Phase 2: Unified Incremental Cursors

Boyar retains `collector:boyar:last_article_id`; no key reset/migration is required.
Sina uses `collector:sina:last_date` for spot report business dates and the independent
`collector:sina:last_date:futures` for quote business dates. Dates use YYYY-MM-DD.
The initial Sina run returns the current real snapshot; repeating on the same business
dates returns0, not an error. This is a first-daily-snapshot feed, not intraday ticks.

All persistence-enabled paths (async jobs, adapter runs, scheduler runs, and Sina's
synchronous endpoint) stage Python cursor proposals, persist/deduplicate the entire
returned batch, then acknowledge monotonic Redis updates. Failed validation/insertion
does not advance any proposed cursor. A Redis acknowledgement failure marks the run
failed even when some/all rows already exist; retry deduplicates those rows. SQL/Redis
remain separate transactions, so crash/retry can repeat work, not guarantee exactly once.
The legacy Boyar synchronous count-only endpoint does not persist or advance cursors;
use async or adapter runs for production incremental ingestion.

`max_items` is not pagination: a partially returned Sina stream/date is not checkpointed.
Use a batch large enough for the complete daily snapshot (default100; current total41).
Existing dates are skipped independently per stream; no automatic historical backfill
or same-day update capture is promised. Configured futures symbols should remain stable;
adding one mid-day requires explicit backfill. Redis unavailability/corruption fails the
run rather than silently scanning from scratch. Other collectors may opt into the Base
cursor methods without changing collectors that have no configured cursor.

Implementation and verification: `docs/reports/PHASE2_DAY1_TASK2.md`.
