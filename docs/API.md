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

运行指定的采集器。

**请求**:
```bash
curl -X POST http://localhost:18000/api/collectors/run \
  -H "Content-Type: application/json" \
  -d '{
    "collector_id": "boyar",
    "max_items": 10
  }'
```

**请求体**:
```json
{
  "collector_id": "boyar",     // 必填: 采集器ID
  "max_items": 10              // 可选: 最大采集数量，默认100
}
```

**响应**:
```json
{
  "status": "running",
  "job_id": "job_123456",
  "collector_id": "boyar",
  "started_at": "2026-10-21T10:00:00Z"
}
```

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
