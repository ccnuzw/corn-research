# CornV2 API 规范

- 规范格式：OpenAPI 3.0.3。
- 文档日期：2026-10-22。
- 服务地址：`http://localhost:18000`。API 路径已包含 `/api`，健康检查为 `/health`。
- 范围：现有接口契约快照中的 46 个 HTTP 操作（37 个不同路径）；同一路径的不同方法分别列出。
- 本文直接由现有 `docs/openapi.yaml` 快照生成；本次未运行验证器、接口测试、镜像构建或部署。
- 所有示例均用于说明结构，不代表实时行情、实际记录数或生产执行结果。
- 当前接口无认证；生产使用应置于可信网络或具备认证的网关之后。

## 1. 通用约定

JSON 请求使用 `Content-Type: application/json`；无请求体的操作不需要发送空 JSON。
日期通常为 `YYYY-MM-DD`，时间为带时区的 RFC 3339。中文查询参数请使用 URL 编码。
列表大多直接返回数组，不含 `total`；分页参数和上限以各操作定义为准，不能假定所有列表都支持 `offset`。
对象中大多数可空字段会输出 `null`；通知的 `metadata` 没有值时会省略。
数据库 Decimal 在采集记录、原始记录和标准记录中序列化为字符串（如 `"2040.0000"`）；`MarketData.value` 则为 JSON 数值。

常见成功响应：

```json
{"success": true, "data": [], "message": null}
```

创建数据源、适配器和调度任务成功时使用 HTTP 200，不是 201；异步采集提交使用 HTTP 202。
客户端应同时检查 HTTP 状态与 `success` 字段。通知、血统和自动提升等接口可能以 HTTP 200 返回业务失败。

### 1.1 主题过滤

`GET /api/data/latest` 支持以下主题映射；同时传入 `indicator` 时以 AND 组合。未知主题按指标名精确过滤。

| topic | 匹配的指标 |
| --- | --- |
| `shandong_arrivals` / `corn_arrivals` | 山东到车量、山东深加工到车量 |
| `corn_spot_price` | 玉米现货价格 |
| `corn_futures_price` | 玉米期货价格 |
| `north_port_inventory` | 北方四港库存 |
| `north_port_shipping` | 北方四港下海量 |

注意：`/api/records?topic=...` 不使用此映射，而是直接匹配原始 `indicator_name`；`/api/topics/{name}/records` 匹配采集记录的 `topic_name`。

### 1.2 执行模式

| 入口 | 返回时机 | 查询执行结果 |
| --- | --- | --- |
| `POST /api/collectors/run`、`POST /api/collectors/{id}/run` | 同步等待完成 | 响应及采集历史 |
| `POST /api/collectors/run/async` | HTTP 202，立即返回 `job_id` | `GET /api/jobs/{id}` |
| `POST /api/adapters/{id}/run` | HTTP 200，立即返回 `run_id` | `GET /api/adapters/{id}/runs` |
| `POST /api/scheduler/jobs/{id}` | HTTP 200，立即返回 `execution_id` | `GET /api/scheduler/jobs/{id}/executions` |

适配器的 `/start`、`/stop` 仅更新数据库状态，不启动或取消采集进程。异步队列状态为 `queued → running → succeeded/failed`；调度执行状态为 `running → success/failed`，成功状态拼写不同。

调度使用 UTC 六字段 Cron（含秒）：北京时间每日 08:00 对应 `0 0 0 * * *`，09:00 对应 `0 0 1 * * *`。当前契约不承诺失败自动重试或停机补跑。

## 2. 错误码与错误格式

当前未定义统一的字符串业务错误码（如 `DATABASE_ERROR`）。下面的错误码指 HTTP 状态码，具体格式因处理函数而异。

| HTTP 状态 | 含义与注意事项 |
| --- | --- |
| `200` | 成功；部分接口也以 `success:false` 表示业务失败；批量标准化需另看 `error_count`。 |
| `202` | 异步采集已入队，不代表采集完成。 |
| `400` | 参数非法、路径/查询/JSON 语法解析失败；部分调度数据库错误也使用此状态。 |
| `404` | 指定资源不存在，或路径未注册；并非所有未知资源都使用此状态。 |
| `405` | 路径存在但 HTTP 方法不支持（框架响应）。 |
| `409` | 异步任务重复提交、调度任务运行中等状态冲突。 |
| `413` | JSON 请求体超过框架限制，默认通常为 2 MiB。 |
| `415` | JSON 请求的 Content-Type 缺失或不正确。 |
| `422` | JSON 字段缺失、类型不匹配、重复别名字段等结构错误。 |
| `500` | 数据库、Redis、Python 调用、序列化或内部处理失败；部分接口另有降级语义。 |
| `501` | 调度任务编辑接口尚未实现。 |

### 2.1 CornError JSON

采集器、数据查询、异步任务等接口的应用错误通常为：

```json
{"success": false, "error": "days must be 1..36500 and limit must be 1..10000"}
```

### 2.2 空响应体

数据源、适配器、主题和兼容记录查询等处理函数可能直接返回 400/404/500，响应体为空；不要无条件对错误体调用 JSON 解析。

### 2.3 纯文本错误

调度错误与 Axum 参数提取错误通常为 `text/plain`。例如调度编辑的 HTTP 501：

```text
Schedule editing is not supported; disable/delete and recreate the job
```

### 2.4 HTTP 200 的业务失败

```json
{"success": false, "data": null, "message": "Record not found"}
```

自动提升失败时 `data` 可能仍为 `{"promoted_count":0}`。批量标准化即使全部失败也可能 `success:true`，必须读取 `success_count` 和 `error_count`。

## 3. 全部端点

| 序号 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 1 | `GET` | `/health` | 存活检查 |
| 2 | `GET` | `/api/sources` | 列出数据源 |
| 3 | `POST` | `/api/sources` | 创建数据源 |
| 4 | `GET` | `/api/sources/{id}` | 查询单个数据源 |
| 5 | `PUT` | `/api/sources/{id}` | 修改数据源 |
| 6 | `DELETE` | `/api/sources/{id}` | 删除数据源 |
| 7 | `GET` | `/api/adapters` | 列出适配器 |
| 8 | `POST` | `/api/adapters` | 创建适配器 |
| 9 | `GET` | `/api/adapters/{id}` | 查询单个适配器 |
| 10 | `PUT` | `/api/adapters/{id}` | 修改适配器 |
| 11 | `DELETE` | `/api/adapters/{id}` | 删除适配器 |
| 12 | `POST` | `/api/adapters/{id}/run` | 后台执行适配器 |
| 13 | `POST` | `/api/adapters/{id}/start` | 设置适配器为running |
| 14 | `POST` | `/api/adapters/{id}/stop` | 设置适配器为stopped |
| 15 | `GET` | `/api/adapters/{id}/runs` | 适配器运行历史 |
| 16 | `GET` | `/api/adapters/{id}/records` | 适配器采集记录 |
| 17 | `GET` | `/api/topics` | 主题列表 |
| 18 | `GET` | `/api/topics/{name}` | 主题详情 |
| 19 | `GET` | `/api/topics/{name}/records` | 按主题查询采集记录 |
| 20 | `GET` | `/api/records` | 兼容原始记录查询 |
| 21 | `GET` | `/api/collectors` | 采集器列表（静态） |
| 22 | `POST` | `/api/collectors/run` | 按名称同步采集 |
| 23 | `POST` | `/api/collectors/{id}/run` | 按路径名称同步采集 |
| 24 | `GET` | `/api/collectors/{id}/history` | 采集器历史 |
| 25 | `GET` | `/api/collectors/{id}/status` | 采集器状态（占位） |
| 26 | `POST` | `/api/collectors/run/async` | 提交持久化后台采集 |
| 27 | `GET` | `/api/jobs/{id}` | 查询后台任务 |
| 28 | `GET` | `/api/data/latest` | 最新市场数据 |
| 29 | `GET` | `/api/data/stats` | 原始数据统计 |
| 30 | `GET` | `/api/data/trend` | 指标趋势 |
| 31 | `GET` | `/api/data/indicators` | 指标列表 |
| 32 | `GET` | `/api/quality/scores` | 质量分数（占位） |
| 33 | `GET` | `/api/quality/distribution` | 质量分布（占位） |
| 34 | `GET` | `/api/quality/issues` | 问题数据（占位） |
| 35 | `GET` | `/api/data/{id}/lineage` | 标准记录血统 |
| 36 | `POST` | `/api/data/standardize` | 批量标准化 |
| 37 | `POST` | `/api/data/auto-promote` | 自动提升合格原始数据 |
| 38 | `GET` | `/api/notifications` | 通知历史 |
| 39 | `POST` | `/api/notifications/mark-read` | 通知标为已读 |
| 40 | `GET` | `/api/scheduler/jobs` | 调度任务列表 |
| 41 | `POST` | `/api/scheduler/jobs` | 创建调度任务 |
| 42 | `POST` | `/api/scheduler/jobs/{id}` | 手动触发调度任务 |
| 43 | `PUT` | `/api/scheduler/jobs/{id}` | 修改调度任务（未实现） |
| 44 | `DELETE` | `/api/scheduler/jobs/{id}` | 删除调度任务 |
| 45 | `PUT` | `/api/scheduler/jobs/{id}/enable` | 启用/停用调度任务 |
| 46 | `GET` | `/api/scheduler/jobs/{id}/executions` | 调度执行历史 |

## 4. 逐端点参数与示例

下列 curl 为调用示例，不会由本文生成过程执行。POST/PUT/DELETE 示例可能修改数据或触发采集，执行前请确认环境。

### 4.1 GET /health

存活检查

固定返回存活字符串；不检查 PostgreSQL、Redis、采集器或调度器就绪状态。

路径/查询参数：无。

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/health'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": "Corn Backend V2 is running",
  "message": null
}
```

### 4.2 GET /api/sources

列出数据源

按名称升序。无分页。

路径/查询参数：无。

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/sources'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": [
    {
      "id": "source_sina",
      "name": "新浪财经",
      "domain": "finance.sina.com.cn",
      "description": "玉米市场价格",
      "status": "active",
      "created_at": "2026-10-22T01:00:00Z",
      "updated_at": "2026-10-22T01:00:00Z"
    }
  ],
  "message": null
}
```

**错误响应示例：HTTP 500**

响应体为空。

### 4.3 POST /api/sources

创建数据源

成功 HTTP 200（不是 201）。状态初始化为 active。 重复主键或外键错误目前返回 500，不是 409。

路径/查询参数：无。

**JSON 请求体**



| 字段 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- |
| `id` | 是 | string |  |
| `name` | 是 | string |  |
| `domain` | 否 | string / null |  |
| `description` | 否 | string / null |  |

**请求体示例**

```json
{
  "id": "source_example",
  "name": "示例数据源",
  "domain": "example.org",
  "description": "示例"
}
```

**请求示例**

```bash
curl -i -X POST 'http://localhost:18000/api/sources' \
  -H 'Content-Type: application/json' \
  --data-raw '{"id":"source_example","name":"示例数据源","domain":"example.org","description":"示例"}'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |
| `413` | JSON 请求体超过默认限制（通常为 2 MiB）。 | text/plain |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |
| `422` | JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。 | text/plain |
| `415` | JSON 请求缺少或使用了错误的 Content-Type。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "id": "source_sina",
    "name": "新浪财经",
    "domain": "finance.sina.com.cn",
    "description": "玉米市场价格",
    "status": "active",
    "created_at": "2026-10-22T01:00:00Z",
    "updated_at": "2026-10-22T01:00:00Z"
  },
  "message": "Source created successfully"
}
```

**错误响应示例：HTTP 500**

响应体为空。

### 4.4 GET /api/sources/{id}

查询单个数据源

查询单个数据源

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string | 路径标识；不是查询参数。 |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/sources/source_sina'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `404` | 资源不存在。 空响应体。 | 空响应体 |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "id": "source_sina",
    "name": "新浪财经",
    "domain": "finance.sina.com.cn",
    "description": "玉米市场价格",
    "status": "active",
    "created_at": "2026-10-22T01:00:00Z",
    "updated_at": "2026-10-22T01:00:00Z"
  },
  "message": null
}
```

**错误响应示例：HTTP 404**

响应体为空。

### 4.5 PUT /api/sources/{id}

修改数据源

部分更新；null 与未提供字段都不修改。无法用 null 清空 domain/description。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string | 路径标识；不是查询参数。 |

**JSON 请求体**

所有字段可选；null 与缺省都表示不修改，不能用 null 清空字段。

| 字段 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- |
| `name` | 否 | string / null |  |
| `domain` | 否 | string / null |  |
| `description` | 否 | string / null |  |
| `status` | 否 | string / null |  |

**请求体示例**

```json
{
  "name": "更新后的名称"
}
```

**请求示例**

```bash
curl -i -X PUT 'http://localhost:18000/api/sources/source_sina' \
  -H 'Content-Type: application/json' \
  --data-raw '{"name":"更新后的名称"}'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `404` | 资源不存在。 空响应体。 | 空响应体 |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |
| `413` | JSON 请求体超过默认限制（通常为 2 MiB）。 | text/plain |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |
| `422` | JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。 | text/plain |
| `415` | JSON 请求缺少或使用了错误的 Content-Type。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "id": "source_sina",
    "name": "新浪财经",
    "domain": "finance.sina.com.cn",
    "description": "玉米市场价格",
    "status": "active",
    "created_at": "2026-10-22T01:00:00Z",
    "updated_at": "2026-10-22T01:00:00Z"
  },
  "message": "Source updated successfully"
}
```

**错误响应示例：HTTP 404**

响应体为空。

### 4.6 DELETE /api/sources/{id}

删除数据源

资源不存在也成功。可能级联删除关联记录/运行历史；async_jobs 外键限制可能导致 500。生产调用前确认依赖和备份。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string | 路径标识；不是查询参数。 |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X DELETE 'http://localhost:18000/api/sources/source_sina'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": "Source deleted successfully",
  "message": null
}
```

**错误响应示例：HTTP 500**

响应体为空。

### 4.7 GET /api/adapters

列出适配器

按 created_at 降序。source 为平铺适配器旁的关联字段。无分页。

路径/查询参数：无。

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/adapters'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": [
    {
      "id": "adapter_sina_spot",
      "name": "新浪玉米现货",
      "script_file": "sina_production",
      "source_id": "source_sina",
      "topic_name": "corn_spot_price",
      "status": "stopped",
      "last_run_at": null,
      "last_cursor": null,
      "total_runs": 0,
      "successful_runs": 0,
      "failed_runs": 0,
      "last_error": null,
      "created_at": "2026-10-22T01:00:00Z",
      "updated_at": "2026-10-22T01:00:00Z",
      "source": {
        "id": "source_sina",
        "name": "新浪财经",
        "domain": "finance.sina.com.cn",
        "description": "玉米市场价格",
        "status": "active",
        "created_at": "2026-10-22T01:00:00Z",
        "updated_at": "2026-10-22T01:00:00Z"
      }
    }
  ],
  "message": null
}
```

**错误响应示例：HTTP 500**

响应体为空。

### 4.8 POST /api/adapters

创建适配器

成功 HTTP 200（不是 201）。状态初始化为 stopped，计数器为 0；此处不验证 Python 脚本可运行性。 重复主键或外键错误目前返回 500，不是 409。

路径/查询参数：无。

**JSON 请求体**



| 字段 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- |
| `id` | 是 | string |  |
| `name` | 是 | string |  |
| `script_file` | 是 | string |  |
| `source_id` | 是 | string |  |
| `topic_name` | 是 | string |  |

**请求体示例**

```json
{
  "id": "adapter_example",
  "name": "示例适配器",
  "script_file": "sina_production",
  "source_id": "source_example",
  "topic_name": "corn_spot_price"
}
```

**请求示例**

```bash
curl -i -X POST 'http://localhost:18000/api/adapters' \
  -H 'Content-Type: application/json' \
  --data-raw '{"id":"adapter_example","name":"示例适配器","script_file":"sina_production","source_id":"source_example","topic_name":"corn_spot_price"}'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |
| `413` | JSON 请求体超过默认限制（通常为 2 MiB）。 | text/plain |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |
| `422` | JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。 | text/plain |
| `415` | JSON 请求缺少或使用了错误的 Content-Type。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "id": "adapter_sina_spot",
    "name": "新浪玉米现货",
    "script_file": "sina_production",
    "source_id": "source_sina",
    "topic_name": "corn_spot_price",
    "status": "stopped",
    "last_run_at": null,
    "last_cursor": null,
    "total_runs": 0,
    "successful_runs": 0,
    "failed_runs": 0,
    "last_error": null,
    "created_at": "2026-10-22T01:00:00Z",
    "updated_at": "2026-10-22T01:00:00Z"
  },
  "message": "Adapter created successfully"
}
```

**错误响应示例：HTTP 500**

响应体为空。

### 4.9 GET /api/adapters/{id}

查询单个适配器

查询单个适配器

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string | 路径标识；不是查询参数。 |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/adapters/adapter_sina_spot'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `404` | 资源不存在。 空响应体。 | 空响应体 |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "id": "adapter_sina_spot",
    "name": "新浪玉米现货",
    "script_file": "sina_production",
    "source_id": "source_sina",
    "topic_name": "corn_spot_price",
    "status": "stopped",
    "last_run_at": null,
    "last_cursor": null,
    "total_runs": 0,
    "successful_runs": 0,
    "failed_runs": 0,
    "last_error": null,
    "created_at": "2026-10-22T01:00:00Z",
    "updated_at": "2026-10-22T01:00:00Z",
    "source": {
      "id": "source_sina",
      "name": "新浪财经",
      "domain": "finance.sina.com.cn",
      "description": "玉米市场价格",
      "status": "active",
      "created_at": "2026-10-22T01:00:00Z",
      "updated_at": "2026-10-22T01:00:00Z"
    }
  },
  "message": null
}
```

**错误响应示例：HTTP 404**

响应体为空。

### 4.10 PUT /api/adapters/{id}

修改适配器

部分更新；null 与未提供字段都不修改。仅 name/script_file/topic_name 可更新。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string | 路径标识；不是查询参数。 |

**JSON 请求体**

不能通过该接口更改 source_id 或 status；null 不更新字段。

| 字段 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- |
| `name` | 否 | string / null |  |
| `script_file` | 否 | string / null |  |
| `topic_name` | 否 | string / null |  |

**请求体示例**

```json
{
  "name": "更新后的适配器名称"
}
```

**请求示例**

```bash
curl -i -X PUT 'http://localhost:18000/api/adapters/adapter_sina_spot' \
  -H 'Content-Type: application/json' \
  --data-raw '{"name":"更新后的适配器名称"}'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `404` | 资源不存在。 空响应体。 | 空响应体 |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |
| `413` | JSON 请求体超过默认限制（通常为 2 MiB）。 | text/plain |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |
| `422` | JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。 | text/plain |
| `415` | JSON 请求缺少或使用了错误的 Content-Type。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "id": "adapter_sina_spot",
    "name": "新浪玉米现货",
    "script_file": "sina_production",
    "source_id": "source_sina",
    "topic_name": "corn_spot_price",
    "status": "stopped",
    "last_run_at": null,
    "last_cursor": null,
    "total_runs": 0,
    "successful_runs": 0,
    "failed_runs": 0,
    "last_error": null,
    "created_at": "2026-10-22T01:00:00Z",
    "updated_at": "2026-10-22T01:00:00Z"
  },
  "message": "Adapter updated successfully"
}
```

**错误响应示例：HTTP 404**

响应体为空。

### 4.11 DELETE /api/adapters/{id}

删除适配器

资源不存在也成功。可能级联删除关联记录/运行历史；async_jobs 外键限制可能导致 500。生产调用前确认依赖和备份。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string | 路径标识；不是查询参数。 |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X DELETE 'http://localhost:18000/api/adapters/adapter_sina_spot'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": "Adapter deleted successfully",
  "message": null
}
```

**错误响应示例：HTTP 500**

响应体为空。

### 4.12 POST /api/adapters/{id}/run

后台执行适配器

创建 collection_runs 后后台执行，立即返回 HTTP 200 和 run_id。固定 max_items=100；不是 async_jobs，不返回 job_id。轮询 /api/adapters/{id}/runs；本端点未防止重复并发提交。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string | 路径标识；不是查询参数。 |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X POST 'http://localhost:18000/api/adapters/adapter_sina_spot/run'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `404` | 资源不存在。 空响应体。 | 空响应体 |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "run_id": "f55ce408-550f-400a-8a03-94839115ac6a",
    "status": "running",
    "message": "Collection started for adapter: 新浪玉米现货"
  },
  "message": null
}
```

**错误响应示例：HTTP 404**

响应体为空。

### 4.13 POST /api/adapters/{id}/start

设置适配器为running

仅更新数据库状态；不会启动/停止 Python 进程，不会创建/取消定时任务，也不会中止正在运行的采集。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string | 路径标识；不是查询参数。 |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X POST 'http://localhost:18000/api/adapters/adapter_sina_spot/start'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `404` | 资源不存在。 空响应体。 | 空响应体 |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "id": "adapter_sina_spot",
    "name": "新浪玉米现货",
    "script_file": "sina_production",
    "source_id": "source_sina",
    "topic_name": "corn_spot_price",
    "status": "running",
    "last_run_at": null,
    "last_cursor": null,
    "total_runs": 0,
    "successful_runs": 0,
    "failed_runs": 0,
    "last_error": null,
    "created_at": "2026-10-22T01:00:00Z",
    "updated_at": "2026-10-22T01:00:00Z"
  },
  "message": "Adapter started"
}
```

**错误响应示例：HTTP 404**

响应体为空。

### 4.14 POST /api/adapters/{id}/stop

设置适配器为stopped

仅更新数据库状态；不会启动/停止 Python 进程，不会创建/取消定时任务，也不会中止正在运行的采集。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string | 路径标识；不是查询参数。 |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X POST 'http://localhost:18000/api/adapters/adapter_sina_spot/stop'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `404` | 资源不存在。 空响应体。 | 空响应体 |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "id": "adapter_sina_spot",
    "name": "新浪玉米现货",
    "script_file": "sina_production",
    "source_id": "source_sina",
    "topic_name": "corn_spot_price",
    "status": "stopped",
    "last_run_at": null,
    "last_cursor": null,
    "total_runs": 0,
    "successful_runs": 0,
    "failed_runs": 0,
    "last_error": null,
    "created_at": "2026-10-22T01:00:00Z",
    "updated_at": "2026-10-22T01:00:00Z"
  },
  "message": "Adapter stopped"
}
```

**错误响应示例：HTTP 404**

响应体为空。

### 4.15 GET /api/adapters/{id}/runs

适配器运行历史

验证适配器存在；started_at DESC、id DESC；仅数组，无总数。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string | 路径标识；不是查询参数。 |
| `limit` | query | 否 | integer | 返回条数，u64。 默认: `20`；最小: `1`；最大: `100` |
| `offset` | query | 否 | integer | 跳过条数，u64；未显式验证 PostgreSQL int64 上界。 默认: `0`；最小: `0` |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/adapters/adapter_sina_spot/runs?limit=20&offset=0'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `400` | 参数非法或调度操作失败。 空响应体。 Axum 提取失败时为 text/plain。 | text/plain |
| `404` | 资源不存在。 空响应体。 | 空响应体 |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": [
    {
      "id": "f55ce408-550f-400a-8a03-94839115ac6a",
      "adapter_id": "adapter_sina_spot",
      "started_at": "2026-10-22T01:00:00Z",
      "completed_at": "2026-10-22T01:00:20Z",
      "status": "success",
      "new_records": 1,
      "duplicate_records": 0,
      "failed_records": 0,
      "start_cursor": null,
      "end_cursor": "2026-10-22",
      "error_message": null,
      "records_collected": 1
    }
  ],
  "message": null
}
```

**错误响应示例：HTTP 400**

```text
Failed to deserialize query string: invalid digit found in string
```

### 4.16 GET /api/adapters/{id}/records

适配器采集记录

查询 collection_records，business_date DESC；保留企业/合约维度。适配器不存在返回空数组而非 404。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string | 路径标识；不是查询参数。 |
| `limit` | query | 否 | integer | u64；没有显式上限，建议小批量查询。 默认: `50`；最小: `0` |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/adapters/adapter_sina_spot/records?limit=1'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": [
    {
      "id": "f55ce408-550f-400a-8a03-94839115ac6a",
      "adapter_id": "adapter_sina_spot",
      "business_date": "2026-10-22",
      "value": "2040.0000",
      "unit": "元/吨",
      "topic_name": "corn_spot_price",
      "record_key": "sina:example-processor:2026-10-22",
      "indicator": "玉米现货价格",
      "region": "山东",
      "metadata": {
        "enterprise": "示例企业（非实测数据）"
      },
      "source_url": "https://finance.sina.com.cn/money/future/C/",
      "source_html_path": null,
      "quality_grade": "B",
      "quality_score": null,
      "collected_at": "2026-10-22T01:00:00Z",
      "created_at": "2026-10-22T01:00:00Z"
    }
  ],
  "message": null
}
```

**错误响应示例：HTTP 500**

响应体为空。

### 4.17 GET /api/topics

主题列表

按适配器 topic_name 分组，按名称排序。record_count 恒为 0、latest_date 恒为 null（尚未实现真实统计）。

路径/查询参数：无。

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/topics'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": [
    {
      "name": "corn_spot_price",
      "adapter_count": 1,
      "record_count": 0,
      "latest_date": null
    }
  ],
  "message": null
}
```

**错误响应示例：HTTP 500**

响应体为空。

### 4.18 GET /api/topics/{name}

主题详情

未知主题返回 200，adapters=[]、record_count=0。record_count 查询错误也被降级为 0，不能据此判断数据库健康。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | path | 是 | string | 路径标识；不是查询参数。 |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/topics/corn_spot_price'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "name": "corn_spot_price",
    "adapters": [
      {
        "id": "adapter_sina_spot",
        "name": "新浪玉米现货",
        "script_file": "sina_production",
        "source_id": "source_sina",
        "topic_name": "corn_spot_price",
        "status": "stopped",
        "last_run_at": null,
        "last_cursor": null,
        "total_runs": 0,
        "successful_runs": 0,
        "failed_runs": 0,
        "last_error": null,
        "created_at": "2026-10-22T01:00:00Z",
        "updated_at": "2026-10-22T01:00:00Z",
        "source": {
          "id": "source_sina",
          "name": "新浪财经",
          "domain": "finance.sina.com.cn",
          "description": "玉米市场价格",
          "status": "active",
          "created_at": "2026-10-22T01:00:00Z",
          "updated_at": "2026-10-22T01:00:00Z"
        }
      }
    ],
    "record_count": 1
  },
  "message": null
}
```

**错误响应示例：HTTP 500**

响应体为空。

### 4.19 GET /api/topics/{name}/records

按主题查询采集记录

collection_records.topic_name 精确匹配，business_date DESC。日期参数未生效。未知主题返回 []。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | path | 是 | string | 路径标识；不是查询参数。 |
| `start_date` | query | 否 | string | 当前被接受但未用于 SQL 过滤；不要依赖此参数。 |
| `end_date` | query | 否 | string | 当前被接受但未用于 SQL 过滤；不要依赖此参数。 |
| `limit` | query | 否 | integer | u64，无显式上限。 默认: `100`；最小: `0` |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/topics/corn_spot_price/records?limit=1'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": [
    {
      "id": "f55ce408-550f-400a-8a03-94839115ac6a",
      "adapter_id": "adapter_sina_spot",
      "business_date": "2026-10-22",
      "value": "2040.0000",
      "unit": "元/吨",
      "topic_name": "corn_spot_price",
      "record_key": "sina:example-processor:2026-10-22",
      "indicator": "玉米现货价格",
      "region": "山东",
      "metadata": {
        "enterprise": "示例企业（非实测数据）"
      },
      "source_url": "https://finance.sina.com.cn/money/future/C/",
      "source_html_path": null,
      "quality_grade": "B",
      "quality_score": null,
      "collected_at": "2026-10-22T01:00:00Z",
      "created_at": "2026-10-22T01:00:00Z"
    }
  ],
  "message": null
}
```

**错误响应示例：HTTP 500**

响应体为空。

### 4.20 GET /api/records

兼容原始记录查询

查询 raw_collection_records 后映射成 CollectionRecord；不保留完整企业/合约元数据。record_key=""，indicator/metadata/quality_* 等为 null。按业务日期、采集时间降序。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `adapter_id` | query | 否 | string | 实际过滤 raw_collection_records.collector_id，不是 adapters.id。 |
| `topic` | query | 否 | string | 实际精确过滤原始 indicator_name；不支持 topic 别名映射。 |
| `start_date` | query | 否 | string | 当前被接受但未用于 SQL 过滤；不要依赖此参数。 |
| `end_date` | query | 否 | string | 当前被接受但未用于 SQL 过滤；不要依赖此参数。 |
| `quality` | query | 否 | string | 被接受但未生效。 |
| `limit` | query | 否 | integer | u64，无显式上限。 默认: `100`；最小: `0` |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/records?adapter_id=sina_production&topic=%E7%8E%89%E7%B1%B3%E7%8E%B0%E8%B4%A7%E4%BB%B7%E6%A0%BC&limit=1'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `500` | 数据库、采集器或内部错误。 空响应体。 | 空响应体 |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": [
    {
      "id": "f55ce408-550f-400a-8a03-94839115ac6a",
      "adapter_id": "sina_production",
      "business_date": "2026-10-22",
      "value": "2040.0000",
      "unit": "元/吨",
      "topic_name": "玉米现货价格",
      "record_key": "",
      "indicator": null,
      "region": "山东",
      "metadata": null,
      "source_url": "https://finance.sina.com.cn/money/future/C/",
      "source_html_path": null,
      "quality_grade": null,
      "quality_score": null,
      "collected_at": "2026-10-22T01:00:00Z",
      "created_at": "2026-10-22T01:00:00Z"
    }
  ],
  "message": null
}
```

**错误响应示例：HTTP 500**

响应体为空。

### 4.21 GET /api/collectors

采集器列表（静态）

当前工作树硬编码 boyar/sina/dce。status/counters/timestamps 为占位，不反映运行状态；DCE 在旧镜像中可能尚未部署。

路径/查询参数：无。

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/collectors'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": [
    {
      "id": "boyar",
      "name": "博亚和讯",
      "status": "idle",
      "last_run": null,
      "last_success": null,
      "total_runs": 0,
      "success_rate": 0.0
    },
    {
      "id": "sina",
      "name": "新浪财经",
      "status": "idle",
      "last_run": null,
      "last_success": null,
      "total_runs": 0,
      "success_rate": 0.0
    },
    {
      "id": "dce",
      "name": "大连商品交易所",
      "status": "idle",
      "last_run": null,
      "last_success": null,
      "total_runs": 0,
      "success_rate": 0.0
    }
  ],
  "message": null
}
```

### 4.22 POST /api/collectors/run

按名称同步采集

同步等待 Python 完成，可能耗时数分钟。长任务建议使用 /api/collectors/run/async。名称需在 runner 中注册，并唯一映射到适配器；boyar/sina/dce 支持对应 *_production 别名。当前同步入口仅新浪/DCE 执行持久化；旧 Boyar/mock/cft 分支不保证写库或提交游标。返回计数不等于新增入库数，重复/无新数据可为 0。来源可用性取决于外部站点，不承诺固定条数。

路径/查询参数：无。

**JSON 请求体**

必须提供 collector_name 或 collector_id 中的一个；两者同传被 serde 视为重复字段并返回 422。

| 字段 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- |
| `collector_name` | 二选一 | string | 采集器名称；也接受别名字段 collector_id。不可同时传两字段，不可为空白。 |
| `collector_id` | 二选一 | string | collector_name 的兼容别名，与其二选一。 |
| `max_items` | 否 | integer / null | 可选；null 使用默认值。 默认: `100`；最小: `1`；最大: `4294967295` |

**请求体示例**

```json
{
  "collector_name": "sina_production",
  "max_items": 100
}
```

**请求示例**

```bash
curl -i -X POST 'http://localhost:18000/api/collectors/run' \
  -H 'Content-Type: application/json' \
  --data-raw '{"collector_name":"sina_production","max_items":100}'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `400` | 参数非法或调度操作失败。 | application/json, text/plain |
| `500` | 数据库、采集器或内部错误。 | application/json |
| `413` | JSON 请求体超过默认限制（通常为 2 MiB）。 | text/plain |
| `422` | JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。 | text/plain |
| `415` | JSON 请求缺少或使用了错误的 Content-Type。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "collector_id": "sina_production",
    "records_collected": 1,
    "run_id": "f55ce408-550f-400a-8a03-94839115ac6a"
  },
  "message": "Collected 1 records"
}
```

**错误响应示例：HTTP 400**

```json
{
  "success": false,
  "error": "collector_name must not be empty"
}
```

```text
Failed to deserialize the JSON body: EOF while parsing a value
```

### 4.23 POST /api/collectors/{id}/run

按路径名称同步采集

固定 max_items=100，不读取请求体。同步等待 Python 完成，可能耗时数分钟。长任务建议使用 /api/collectors/run/async。名称需在 runner 中注册，并唯一映射到适配器；boyar/sina/dce 支持对应 *_production 别名。当前同步入口仅新浪/DCE 执行持久化；旧 Boyar/mock/cft 分支不保证写库或提交游标。返回计数不等于新增入库数，重复/无新数据可为 0。来源可用性取决于外部站点，不承诺固定条数。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string | 路径标识；不是查询参数。 |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X POST 'http://localhost:18000/api/collectors/sina_production/run'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `400` | 参数非法或调度操作失败。 | application/json, text/plain |
| `500` | 数据库、采集器或内部错误。 | application/json |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "collector_id": "sina_production",
    "records_collected": 1,
    "run_id": "f55ce408-550f-400a-8a03-94839115ac6a"
  },
  "message": "Collected 1 records"
}
```

**错误响应示例：HTTP 400**

```json
{
  "success": false,
  "error": "Unknown collector: missing_collector"
}
```

```text
Failed to deserialize query string: invalid digit found in string
```

### 4.24 GET /api/collectors/{id}/history

采集器历史

按 started_at DESC、id DESC。未知/歧义采集器映射返回 400，而非 404。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string | 路径标识；不是查询参数。 |
| `limit` | query | 否 | integer | 1..100，默认 50。 默认: `50`；最小: `1`；最大: `100` |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/collectors/sina_production/history?limit=10'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `400` | 参数非法或调度操作失败。 | application/json, text/plain |
| `500` | 数据库、采集器或内部错误。 | application/json |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": [
    {
      "id": "f55ce408-550f-400a-8a03-94839115ac6a",
      "collector_id": "sina_production",
      "started_at": "2026-10-22T01:00:00Z",
      "completed_at": "2026-10-22T01:00:20Z",
      "status": "success",
      "records_collected": 1,
      "error_message": null
    }
  ],
  "message": null
}
```

**错误响应示例：HTTP 400**

```json
{
  "success": false,
  "error": "limit must be between 1 and 100"
}
```

```text
Failed to deserialize query string: invalid digit found in string
```

### 4.25 GET /api/collectors/{id}/status

采集器状态（占位）

任意 id 都返回 idle、计数 0、时间 null；未验证采集器存在。查询真实执行状态请用 jobs 或 runs。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string | 路径标识；不是查询参数。 |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/collectors/sina_production/status'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "id": "sina_production",
    "name": "sina_production",
    "status": "idle",
    "last_run": null,
    "last_success": null,
    "total_runs": 0,
    "success_rate": 0.0
  },
  "message": null
}
```

**错误响应示例：HTTP 400**

```text
Failed to deserialize query string: invalid digit found in string
```

### 4.26 POST /api/collectors/run/async

提交持久化后台采集

立即返回 job_id。每适配器最多一个 queued/running 的异步任务，重复提交 409。PostgreSQL 队列由两个后台 worker 轮询；queued 可恢复，重启时未完成 running 通常标失败（已提交成功的关联 run 可恢复成功）。Python 超时 2 小时；没有取消/重放接口。

路径/查询参数：无。

**JSON 请求体**

必须提供 collector_name 或 collector_id 中的一个；两者同传被 serde 视为重复字段并返回 422。

| 字段 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- |
| `collector_name` | 二选一 | string | 采集器名称；也接受别名字段 collector_id。不可同时传两字段，不可为空白。 |
| `collector_id` | 二选一 | string | collector_name 的兼容别名，与其二选一。 |
| `max_items` | 否 | integer / null | 可选；null 使用默认值。 默认: `100`；最小: `1`；最大: `1000` |

**请求体示例**

```json
{
  "collector_name": "boyar_production",
  "max_items": 100
}
```

**请求示例**

```bash
curl -i -X POST 'http://localhost:18000/api/collectors/run/async' \
  -H 'Content-Type: application/json' \
  --data-raw '{"collector_name":"boyar_production","max_items":100}'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `202` | 成功。 | application/json |
| `400` | 参数非法或调度操作失败。 | application/json, text/plain |
| `409` | 存在运行中的任务，或状态冲突。 | application/json |
| `500` | 数据库、采集器或内部错误。 | application/json |
| `413` | JSON 请求体超过默认限制（通常为 2 MiB）。 | text/plain |
| `422` | JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。 | text/plain |
| `415` | JSON 请求缺少或使用了错误的 Content-Type。 | text/plain |

**响应示例：HTTP 202**

```json
{
  "success": true,
  "data": {
    "job_id": "f55ce408-550f-400a-8a03-94839115ac6a",
    "status": "queued",
    "status_url": "/api/jobs/f55ce408-550f-400a-8a03-94839115ac6a"
  },
  "message": "Collection queued"
}
```

**错误响应示例：HTTP 400**

```json
{
  "success": false,
  "error": "collector_name is required; max_items must be 1..1000"
}
```

```text
Failed to deserialize the JSON body: EOF while parsing a value
```

### 4.27 GET /api/jobs/{id}

查询后台任务

job_id 必须 UUID。状态 queued → running → succeeded/failed；仅成功任务进度 100。progress 为阶段进度，不是时间估计；result 成功时通常含 records_collected。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string (uuid) | 路径标识；不是查询参数。 |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/jobs/f55ce408-550f-400a-8a03-94839115ac6a'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `404` | 资源不存在。 | application/json |
| `500` | 数据库、采集器或内部错误。 | application/json |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "id": "f55ce408-550f-400a-8a03-94839115ac6a",
    "collector_name": "boyar_production",
    "adapter_id": "adapter_boyar_shandong",
    "run_id": null,
    "max_items": 100,
    "status": "queued",
    "progress": 0,
    "phase": "queued",
    "details": {},
    "result": null,
    "error_message": null,
    "created_at": "2026-10-22T01:00:00Z",
    "started_at": null,
    "completed_at": null,
    "updated_at": "2026-10-22T01:00:00Z"
  },
  "message": null
}
```

**错误响应示例：HTTP 404**

```json
{
  "success": false,
  "error": "Async job not found"
}
```

### 4.28 GET /api/data/latest

最新市场数据

读取 raw_collection_records；business_date DESC、collected_at DESC。value 是 number，quality 固定为 A，缺失企业/合约 provenance；需要精确来源请查适配器 records。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `topic` | query | 否 | string | 主题映射见通用说明；未知值按 indicator_name 精确过滤。 |
| `indicator` | query | 否 | string | 指标名精确过滤；与 topic 为 AND 关系。 |
| `days` | query | 否 | integer | 以 UTC 今日为上界、今日减 days 为下界，两端均包含。 默认: `30`；最小: `1`；最大: `36500` |
| `limit` | query | 否 | integer | 最大返回条数。 默认: `100`；最小: `1`；最大: `10000` |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/data/latest?topic=corn_spot_price&indicator=%E7%8E%89%E7%B1%B3%E7%8E%B0%E8%B4%A7%E4%BB%B7%E6%A0%BC&days=30&limit=1'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `400` | 参数非法或调度操作失败。 | application/json, text/plain |
| `500` | 数据库、采集器或内部错误。 | application/json |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": [
    {
      "id": "f55ce408-550f-400a-8a03-94839115ac6a",
      "business_date": "2026-10-22",
      "indicator_name": "玉米现货价格",
      "value": 2040.0,
      "unit": "元/吨",
      "source": "sina_production",
      "quality": "A",
      "collected_at": "2026-10-22T01:00:00Z"
    }
  ],
  "message": null
}
```

**错误响应示例：HTTP 400**

```json
{
  "success": false,
  "error": "days must be 1..36500 and limit must be 1..10000"
}
```

```text
Failed to deserialize query string: invalid digit found in string
```

### 4.29 GET /api/data/stats

原始数据统计

统计原始记录。coverage_rate 为占位 85.5/0；当前实现读取全部原始记录进行指标聚合，大数据量时需注意成本。

路径/查询参数：无。

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/data/stats'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `500` | 数据库、采集器或内部错误。 | application/json |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "total_records": 1,
    "indicator_count": 1,
    "coverage_rate": 85.5,
    "latest_collection": "2026-10-22T01:00:00Z"
  },
  "message": null
}
```

**错误响应示例：HTTP 500**

```json
{
  "success": false,
  "error": "Internal error: Database query failed"
}
```

### 4.30 GET /api/data/trend

指标趋势

按 business_date ASC；不聚合、不按企业/合约区分、不提供 limit。quality 固定 A。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `indicator` | query | 是 | string | 必需，指标名精确匹配。 |
| `days` | query | 否 | integer | UTC 日期窗口，含两端。 默认: `30`；最小: `1`；最大: `36500` |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/data/trend?indicator=%E7%8E%89%E7%B1%B3%E7%8E%B0%E8%B4%A7%E4%BB%B7%E6%A0%BC&days=7'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `400` | 参数非法或调度操作失败。 | application/json, text/plain |
| `500` | 数据库、采集器或内部错误。 | application/json |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": [
    {
      "id": "f55ce408-550f-400a-8a03-94839115ac6a",
      "business_date": "2026-10-22",
      "indicator_name": "玉米现货价格",
      "value": 2040.0,
      "unit": "元/吨",
      "source": "sina_production",
      "quality": "A",
      "collected_at": "2026-10-22T01:00:00Z"
    }
  ],
  "message": null
}
```

**错误响应示例：HTTP 400**

```json
{
  "success": false,
  "error": "days must be 1..36500"
}
```

```text
Failed to deserialize query string: invalid digit found in string
```

### 4.31 GET /api/data/indicators

指标列表

扫描全部 raw 记录分组；display_name=name；顺序不保证。

路径/查询参数：无。

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/data/indicators'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `500` | 数据库、采集器或内部错误。 | application/json |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": [
    {
      "name": "玉米现货价格",
      "display_name": "玉米现货价格",
      "unit": "元/吨",
      "record_count": 1
    }
  ],
  "message": null
}
```

**错误响应示例：HTTP 500**

```json
{
  "success": false,
  "error": "Internal error: Database query failed"
}
```

### 4.32 GET /api/quality/scores

质量分数（占位）

当前固定返回空数组，尚未执行质量评分。

路径/查询参数：无。

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/quality/scores'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": [],
  "message": null
}
```

### 4.33 GET /api/quality/distribution

质量分布（占位）

当前固定全零，grade_m 表示 Mock 测试数据类别，不是生产统计。

路径/查询参数：无。

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/quality/distribution'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "grade_a": 0,
    "grade_b": 0,
    "grade_c": 0,
    "grade_d": 0,
    "grade_m": 0
  },
  "message": "质量分布统计(M=Mock测试数据)"
}
```

### 4.34 GET /api/quality/issues

问题数据（占位）

当前固定空数组；未读取 severity 等过滤参数。

路径/查询参数：无。

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/quality/issues'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": [],
  "message": null
}
```

### 4.35 GET /api/data/{id}/lineage

标准记录血统

id 是 STANDARD 表记录 UUID（不是 raw id）。无效 UUID、记录不存在或数据库错误均返回 HTTP 200 + success:false。关联原始记录查询失败也可能降级为 raw_record:null。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string | 路径标识；不是查询参数。 |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/data/f55ce408-550f-400a-8a03-94839115ac6a/lineage'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | HTTP 200 可能包含 success:false，客户端必须检查响应体。 | application/json |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |

**响应示例：HTTP 200**

示例 `success`：

```json
{
  "success": true,
  "data": {
    "standard_record": {
      "id": "ba3c20b5-b049-48d1-9942-d5b04fa7f9ac",
      "business_date": "2026-10-22",
      "indicator_name": "玉米现货价格",
      "value": "2040.0000",
      "unit": "元/吨",
      "region": "山东",
      "quality_grade": "B",
      "quality_score": "90.00",
      "quality_issues": null,
      "source_id": "sina_production",
      "raw_record_id": "f55ce408-550f-400a-8a03-94839115ac6a",
      "collected_at": "2026-10-22T01:00:00Z",
      "standardized_at": "2026-10-22T01:00:00Z",
      "version": 1,
      "is_latest": true,
      "metadata": null,
      "created_at": "2026-10-22T01:00:00Z",
      "updated_at": "2026-10-22T01:00:00Z"
    },
    "raw_record": {
      "id": "f55ce408-550f-400a-8a03-94839115ac6a",
      "collector_id": "sina_production",
      "business_date": "2026-10-22",
      "indicator_name": "玉米现货价格",
      "value": "2040.0000",
      "unit": "元/吨",
      "region": "山东",
      "source_url": "https://finance.sina.com.cn/money/future/C/",
      "original_text": null,
      "dedup_key": "example-key",
      "collected_at": "2026-10-22T01:00:00Z",
      "created_at": "2026-10-22T01:00:00Z",
      "updated_at": "2026-10-22T01:00:00Z"
    },
    "lineage_chain": [
      "原始记录: example-key",
      "采集: sina_production (2026-10-22 01:00)",
      "标准化: 2026-10-22 01:00 (质量等级: B)",
      "版本: 1"
    ]
  },
  "message": null
}
```

示例 `application_failure`：

```json
{
  "success": false,
  "data": null,
  "message": "Record not found"
}
```

**错误响应示例：HTTP 400**

```text
Failed to deserialize query string: invalid digit found in string
```

### 4.36 POST /api/data/standardize

批量标准化

raw_record_ids 必须数组。逐项处理，UUID 无效、未找到或标准化失败计入 error_count；即便全部失败也 HTTP 200 且 success:true。不限制数组长度。

路径/查询参数：无。

**JSON 请求体**



| 字段 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- |
| `raw_record_ids` | 是 | array[string] |  |

**请求体示例**

```json
{
  "raw_record_ids": [
    "f55ce408-550f-400a-8a03-94839115ac6a"
  ]
}
```

**请求示例**

```bash
curl -i -X POST 'http://localhost:18000/api/data/standardize' \
  -H 'Content-Type: application/json' \
  --data-raw '{"raw_record_ids":["f55ce408-550f-400a-8a03-94839115ac6a"]}'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `413` | JSON 请求体超过默认限制（通常为 2 MiB）。 | text/plain |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |
| `422` | JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。 | text/plain |
| `415` | JSON 请求缺少或使用了错误的 Content-Type。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "success_count": 1,
    "error_count": 0
  },
  "message": "Standardized 1 records"
}
```

**错误响应示例：HTTP 413**

```text
Failed to buffer the request body: length limit exceeded
```

### 4.37 POST /api/data/auto-promote

自动提升合格原始数据

不读取请求体；尝试提升最近 24 小时符合 A/B 质量要求、尚未提升的原始记录。业务失败仍返回 HTTP 200，需检查 success。

路径/查询参数：无。

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X POST 'http://localhost:18000/api/data/auto-promote'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | HTTP 200 可能包含 success:false，客户端必须检查响应体。 | application/json |

**响应示例：HTTP 200**

示例 `success`：

```json
{
  "success": true,
  "data": {
    "promoted_count": 1
  },
  "message": "Auto-promoted 1 records"
}
```

示例 `application_failure`：

```json
{
  "success": false,
  "data": {
    "promoted_count": 0
  },
  "message": "Auto-promotion failed: Database error"
}
```

### 4.38 GET /api/notifications

通知历史

从 Redis 读取最新优先通知；Redis 列表最多保留 100 条。metadata 没有值时省略。Redis 错误 HTTP 200 + success:false。无用户隔离。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `limit` | query | 否 | integer | usize，默认 50。未显式校验上限；请使用 1..100。0 存在 limit-1 下溢风险，并非稳定的空列表语义。 默认: `50`；最小: `0` |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/notifications?limit=10'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | HTTP 200 可能包含 success:false，客户端必须检查响应体。 | application/json |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |

**响应示例：HTTP 200**

示例 `success`：

```json
{
  "success": true,
  "data": [
    {
      "id": "f55ce408-550f-400a-8a03-94839115ac6a",
      "level": "error",
      "title": "定时采集失败",
      "message": "示例错误：数据源请求失败",
      "timestamp": "2026-10-22T01:00:00Z"
    }
  ],
  "message": null
}
```

示例 `application_failure`：

```json
{
  "success": false,
  "data": null,
  "message": "Redis operation failed"
}
```

**错误响应示例：HTTP 400**

```text
Failed to deserialize query string: invalid digit found in string
```

### 4.39 POST /api/notifications/mark-read

通知标为已读

添加全局 Redis 已读集合；不验证通知存在，不按用户区分，历史查询不返回已读状态。Redis 失败仍 HTTP 200。

路径/查询参数：无。

**JSON 请求体**



| 字段 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- |
| `notification_id` | 是 | string |  |

**请求体示例**

```json
{
  "notification_id": "f55ce408-550f-400a-8a03-94839115ac6a"
}
```

**请求示例**

```bash
curl -i -X POST 'http://localhost:18000/api/notifications/mark-read' \
  -H 'Content-Type: application/json' \
  --data-raw '{"notification_id":"f55ce408-550f-400a-8a03-94839115ac6a"}'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | HTTP 200 可能包含 success:false，客户端必须检查响应体。 | application/json |
| `413` | JSON 请求体超过默认限制（通常为 2 MiB）。 | text/plain |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |
| `422` | JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。 | text/plain |
| `415` | JSON 请求缺少或使用了错误的 Content-Type。 | text/plain |

**响应示例：HTTP 200**

示例 `success`：

```json
{
  "success": true,
  "data": "Notification marked as read",
  "message": null
}
```

示例 `application_failure`：

```json
{
  "success": false,
  "data": null,
  "message": "Redis operation failed"
}
```

**错误响应示例：HTTP 413**

```text
Failed to buffer the request body: length limit exceeded
```

### 4.40 GET /api/scheduler/jobs

调度任务列表

created_at ASC、id ASC；next_run 可能为 null，不代表自动调度已验证。错误通常是 text/plain，不是 CornError JSON；部分数据库错误当前也映射为 400。Cron 使用 UTC 六字段（含秒）；北京时间 08:00 为 0 0 0 * * *，09:00 为 0 0 1 * * *。未实现自动失败重试或停机补跑。

路径/查询参数：无。

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/scheduler/jobs'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `400` | 参数非法或调度操作失败。 | text/plain |
| `500` | 数据库、采集器或内部错误。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": [
    {
      "id": "f55ce408-550f-400a-8a03-94839115ac6a",
      "name": "新浪每日09:00",
      "collector_id": "sina_production",
      "cron_expression": "0 0 1 * * *",
      "enabled": true,
      "description": null,
      "status": "idle",
      "last_run": null,
      "last_error": null,
      "total_runs": 0,
      "success_count": 0,
      "failed_count": 0,
      "created_at": "2026-10-22T01:00:00Z",
      "next_run": "2026-10-22T01:00:00Z",
      "timezone": "UTC"
    }
  ],
  "message": null
}
```

**错误响应示例：HTTP 400**

```text
Failed to deserialize query string: invalid digit found in string
```

### 4.41 POST /api/scheduler/jobs

创建调度任务

名称不可为空，Cron 校验并验证适配器映射；enabled 默认 true；成功 HTTP 200。错误通常是 text/plain，不是 CornError JSON；部分数据库错误当前也映射为 400。Cron 使用 UTC 六字段（含秒）；北京时间 08:00 为 0 0 0 * * *，09:00 为 0 0 1 * * *。未实现自动失败重试或停机补跑。

路径/查询参数：无。

**JSON 请求体**



| 字段 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- |
| `name` | 是 | string | 不可为空白。 |
| `collector_id` | 是 | string | 必须唯一解析到数据库适配器。 |
| `cron_expression` | 是 | string | UTC，秒 分 时 日 月 周。 |
| `description` | 否 | string / null |  |
| `enabled` | 否 | boolean / null |  默认: `true` |

**请求体示例**

```json
{
  "name": "新浪每日09:00",
  "collector_id": "sina_production",
  "cron_expression": "0 0 1 * * *",
  "description": "北京时间每日09:00采集",
  "enabled": true
}
```

**请求示例**

```bash
curl -i -X POST 'http://localhost:18000/api/scheduler/jobs' \
  -H 'Content-Type: application/json' \
  --data-raw '{"name":"新浪每日09:00","collector_id":"sina_production","cron_expression":"0 0 1 * * *","description":"北京时间每日09:00采集","enabled":true}'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `400` | 参数非法或调度操作失败。 | text/plain |
| `500` | 数据库、采集器或内部错误。 | text/plain |
| `413` | JSON 请求体超过默认限制（通常为 2 MiB）。 | text/plain |
| `422` | JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。 | text/plain |
| `415` | JSON 请求缺少或使用了错误的 Content-Type。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "job_id": "f55ce408-550f-400a-8a03-94839115ac6a"
  },
  "message": null
}
```

**错误响应示例：HTTP 400**

```text
Failed to deserialize the JSON body: EOF while parsing a value
```

### 4.42 POST /api/scheduler/jobs/{id}

手动触发调度任务

创建 job_executions 后后台执行。手动允许触发 disabled 任务；同任务运行时拒绝。不存在/禁用/已运行的共用错误消息映射为 409，因此未知 UUID 也可能是 409（不是 404）。POST 成功不代表采集已成功，请轮询 executions；错误原因写 error_message。错误通常是 text/plain，不是 CornError JSON；部分数据库错误当前也映射为 400。Cron 使用 UTC 六字段（含秒）；北京时间 08:00 为 0 0 0 * * *，09:00 为 0 0 1 * * *。未实现自动失败重试或停机补跑。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string (uuid) | 路径标识；不是查询参数。 |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X POST 'http://localhost:18000/api/scheduler/jobs/f55ce408-550f-400a-8a03-94839115ac6a'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `400` | 参数非法或调度操作失败。 | text/plain |
| `409` | 存在运行中的任务，或状态冲突。 | text/plain |
| `500` | 数据库、采集器或内部错误。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": {
    "execution_id": "f55ce408-550f-400a-8a03-94839115ac6a",
    "status": "running"
  },
  "message": null
}
```

**错误响应示例：HTTP 400**

```text
Invalid URL: Cannot parse UUID
```

### 4.43 PUT /api/scheduler/jobs/{id}

修改调度任务（未实现）

始终返回 501；请禁用/删除后重建。处理函数不解析路径 UUID，也不读取 JSON 请求体。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string | 路径标识；不是查询参数。 |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X PUT 'http://localhost:18000/api/scheduler/jobs/adapter_sina_spot'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `501` | 接口存在，但功能未实现。 | text/plain |
| `400` | 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。 | text/plain |

**响应示例：HTTP 501**

```text
Schedule editing is not supported; disable/delete and recreate the job
```

### 4.44 DELETE /api/scheduler/jobs/{id}

删除调度任务

正在执行时 409；不存在 404。删除同时级联清理执行历史。错误通常是 text/plain，不是 CornError JSON；部分数据库错误当前也映射为 400。Cron 使用 UTC 六字段（含秒）；北京时间 08:00 为 0 0 0 * * *，09:00 为 0 0 1 * * *。未实现自动失败重试或停机补跑。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string (uuid) | 路径标识；不是查询参数。 |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X DELETE 'http://localhost:18000/api/scheduler/jobs/f55ce408-550f-400a-8a03-94839115ac6a'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `400` | 参数非法或调度操作失败。 | text/plain |
| `404` | 资源不存在。 | text/plain |
| `409` | 存在运行中的任务，或状态冲突。 | text/plain |
| `500` | 数据库、采集器或内部错误。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": "Job deleted",
  "message": null
}
```

**错误响应示例：HTTP 400**

```text
Invalid URL: Cannot parse UUID
```

### 4.45 PUT /api/scheduler/jobs/{id}/enable

启用/停用调度任务

更新数据库及运行时注册；停用不会取消正在运行的采集。不存在返回 404。错误通常是 text/plain，不是 CornError JSON；部分数据库错误当前也映射为 400。Cron 使用 UTC 六字段（含秒）；北京时间 08:00 为 0 0 0 * * *，09:00 为 0 0 1 * * *。未实现自动失败重试或停机补跑。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string (uuid) | 路径标识；不是查询参数。 |

**JSON 请求体**



| 字段 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- |
| `enabled` | 是 | boolean |  |

**请求体示例**

```json
{
  "enabled": false
}
```

**请求示例**

```bash
curl -i -X PUT 'http://localhost:18000/api/scheduler/jobs/f55ce408-550f-400a-8a03-94839115ac6a/enable' \
  -H 'Content-Type: application/json' \
  --data-raw '{"enabled":false}'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `400` | 参数非法或调度操作失败。 | text/plain |
| `404` | 资源不存在。 | text/plain |
| `500` | 数据库、采集器或内部错误。 | text/plain |
| `413` | JSON 请求体超过默认限制（通常为 2 MiB）。 | text/plain |
| `422` | JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。 | text/plain |
| `415` | JSON 请求缺少或使用了错误的 Content-Type。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": "Job toggled",
  "message": null
}
```

**错误响应示例：HTTP 400**

```text
Failed to deserialize the JSON body: EOF while parsing a value
```

### 4.46 GET /api/scheduler/jobs/{id}/executions

调度执行历史

按 started_at DESC、id DESC；无 total 字段。无任务时 404。错误通常是 text/plain，不是 CornError JSON；部分数据库错误当前也映射为 400。Cron 使用 UTC 六字段（含秒）；北京时间 08:00 为 0 0 0 * * *，09:00 为 0 0 1 * * *。未实现自动失败重试或停机补跑。

**路径/查询参数**

| 参数 | 位置 | 必需 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | path | 是 | string (uuid) | 路径标识；不是查询参数。 |
| `limit` | query | 否 | integer | 每页条数。 默认: `20`；最小: `1`；最大: `100` |
| `offset` | query | 否 | integer | 跳过条数，必须不超过 int64 最大值。 默认: `0`；最小: `0`；最大: `9223372036854775807` |
| `status` | query | 否 | string | 精确匹配。 允许值: `["running", "success", "failed"]` |
| `start_date` | query | 否 | string (date-time) | started_at 下界，RFC 3339，含边界。URL 中 + 需转义为 %2B。 |
| `end_date` | query | 否 | string (date-time) | started_at 上界，RFC 3339，含边界；不得早于 start_date。 |

请求体：无；该操作不读取 JSON 请求体。

**请求示例**

```bash
curl -i -X GET 'http://localhost:18000/api/scheduler/jobs/f55ce408-550f-400a-8a03-94839115ac6a/executions?limit=20&offset=0&status=failed&start_date=2026-10-01T00%3A00%3A00Z&end_date=2026-10-31T23%3A59%3A59Z'
```

**响应状态**

| HTTP | 说明 | 响应格式 |
| --- | --- | --- |
| `200` | 成功。 | application/json |
| `400` | 参数非法或调度操作失败。 | text/plain |
| `404` | 资源不存在。 | text/plain |
| `500` | 数据库、采集器或内部错误。 | text/plain |

**响应示例：HTTP 200**

```json
{
  "success": true,
  "data": [
    {
      "id": "7d723742-0d18-46fb-8025-61cb1903c647",
      "job_id": "f55ce408-550f-400a-8a03-94839115ac6a",
      "trigger_type": "manual",
      "status": "failed",
      "started_at": "2026-10-22T01:00:00Z",
      "completed_at": "2026-10-22T01:00:01Z",
      "records_collected": 0,
      "collection_run_id": null,
      "error_message": "示例：数据源请求失败"
    }
  ],
  "message": null
}
```

**错误响应示例：HTTP 400**

```text
Invalid URL: Cannot parse UUID
```

## 5. 已知边界

- `/health` 只检查服务存活，不检查依赖就绪。
- 采集器列表/状态、质量接口、主题列表部分统计、覆盖率包含占位值，不能作为真实监控结果。
- 主题记录查询的日期参数，以及通用记录查询的日期/质量参数尚未生效。
- 通知 `limit=0` 存在下溢风险；调用方请使用 1..100，服务端尚未提供相应范围校验。
- 调度编辑接口固定返回 501；自动重试、停机补跑不属于当前已实现契约。
- `/ws/notifications`、`/metrics`、`/api/cache/*`、`/api/data/raw`、`/api/data/standard` 未在本快照中注册，不应当作为可用接口。
- 同步采集可能耗时较长；优先使用异步 job 接口。提交成功不等于数据源可达、采集完成或数据已入库。
- 本文未执行验证；本地代码快照、已运行容器和生产环境可能存在版本差异。

## 6. 完整 OpenAPI 3.0.3 YAML

以下代码块包含 `openapi`、`info`、`servers`、全部 46 个操作、参数、请求体、响应、错误和组件模型，可作为完整规范快照使用。人类可读章节与 YAML 共同来自现有规范；本次仅生成文档，不运行验证。

```yaml
openapi: 3.0.3
info:
  title: CornV2 Backend API
  version: 0.1.0-worktree-2026-10-22
  description: 基于本地 Rust 工作树生成的当前行为契约，不是未来能力承诺。46 个操作；示例为示意，不代表实时行情或真实采集条数。无认证，生产环境必须在可信网络或有认证的网关后使用。
servers:
- url: http://localhost:18000
  description: 本地 Docker 映射端口，路径已包含 /api（health 除外）。
tags:
- name: Health
- name: Sources
- name: Adapters
- name: Topics
- name: Records
- name: Collectors
- name: AsyncJobs
- name: Data
- name: Quality
- name: Lineage
- name: Notifications
- name: Scheduler
security: []
paths:
  /health:
    get:
      operationId: health_check
      tags:
      - Health
      summary: 存活检查
      description: 固定返回存活字符串；不检查 PostgreSQL、Redis、采集器或调度器就绪状态。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: string
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: Corn Backend V2 is running
                message: null
      x-source-handler: health_check
  /api/sources:
    get:
      operationId: list_sources
      tags:
      - Sources
      summary: 列出数据源
      description: 按名称升序。无分页。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Source'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data:
                - &id001
                  id: source_sina
                  name: 新浪财经
                  domain: finance.sina.com.cn
                  description: 玉米市场价格
                  status: active
                  created_at: '2026-10-22T01:00:00Z'
                  updated_at: '2026-10-22T01:00:00Z'
                message: null
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
      x-source-handler: collection_handlers::list_sources
    post:
      operationId: create_source
      tags:
      - Sources
      summary: 创建数据源
      description: 成功 HTTP 200（不是 201）。状态初始化为 active。 重复主键或外键错误目前返回 500，不是 409。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/Source'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: *id001
                message: Source created successfully
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
        '413':
          description: JSON 请求体超过默认限制（通常为 2 MiB）。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to buffer the request body: length limit exceeded'
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize the JSON body: EOF while parsing a value'
        '422':
          description: JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。
          content:
            text/plain:
              schema:
                type: string
              example: Failed to deserialize the JSON body into the target type
        '415':
          description: JSON 请求缺少或使用了错误的 Content-Type。
          content:
            text/plain:
              schema:
                type: string
              example: 'Expected request with `Content-Type: application/json`'
      x-source-handler: collection_handlers::create_source
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateSource'
            example: &id049
              id: source_example
              name: 示例数据源
              domain: example.org
              description: 示例
  /api/sources/{id}:
    get:
      operationId: get_source
      tags:
      - Sources
      summary: 查询单个数据源
      description: 查询单个数据源
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/Source'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: *id001
                message: null
        '404':
          description: 资源不存在。 空响应体。
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
      x-source-handler: collection_handlers::get_source
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema:
          type: string
        example: source_sina
    put:
      operationId: update_source
      tags:
      - Sources
      summary: 修改数据源
      description: 部分更新；null 与未提供字段都不修改。无法用 null 清空 domain/description。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/Source'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: *id001
                message: Source updated successfully
        '404':
          description: 资源不存在。 空响应体。
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
        '413':
          description: JSON 请求体超过默认限制（通常为 2 MiB）。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to buffer the request body: length limit exceeded'
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize the JSON body: EOF while parsing a value'
        '422':
          description: JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。
          content:
            text/plain:
              schema:
                type: string
              example: Failed to deserialize the JSON body into the target type
        '415':
          description: JSON 请求缺少或使用了错误的 Content-Type。
          content:
            text/plain:
              schema:
                type: string
              example: 'Expected request with `Content-Type: application/json`'
      x-source-handler: collection_handlers::update_source
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema:
          type: string
        example: source_sina
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UpdateSource'
            example: &id050
              name: 更新后的名称
    delete:
      operationId: delete_source
      tags:
      - Sources
      summary: 删除数据源
      description: 资源不存在也成功。可能级联删除关联记录/运行历史；async_jobs 外键限制可能导致 500。生产调用前确认依赖和备份。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: string
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: Source deleted successfully
                message: null
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
      x-source-handler: collection_handlers::delete_source
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema:
          type: string
        example: source_sina
  /api/adapters:
    get:
      operationId: list_adapters
      tags:
      - Adapters
      summary: 列出适配器
      description: 按 created_at 降序。source 为平铺适配器旁的关联字段。无分页。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/AdapterWithSource'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data:
                - &id002
                  id: adapter_sina_spot
                  name: 新浪玉米现货
                  script_file: sina_production
                  source_id: source_sina
                  topic_name: corn_spot_price
                  status: stopped
                  last_run_at: null
                  last_cursor: null
                  total_runs: 0
                  successful_runs: 0
                  failed_runs: 0
                  last_error: null
                  created_at: '2026-10-22T01:00:00Z'
                  updated_at: '2026-10-22T01:00:00Z'
                  source: *id001
                message: null
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
      x-source-handler: collection_handlers::list_adapters
    post:
      operationId: create_adapter
      tags:
      - Adapters
      summary: 创建适配器
      description: 成功 HTTP 200（不是 201）。状态初始化为 stopped，计数器为 0；此处不验证 Python 脚本可运行性。 重复主键或外键错误目前返回 500，不是 409。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/Adapter'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: &id003
                  id: adapter_sina_spot
                  name: 新浪玉米现货
                  script_file: sina_production
                  source_id: source_sina
                  topic_name: corn_spot_price
                  status: stopped
                  last_run_at: null
                  last_cursor: null
                  total_runs: 0
                  successful_runs: 0
                  failed_runs: 0
                  last_error: null
                  created_at: '2026-10-22T01:00:00Z'
                  updated_at: '2026-10-22T01:00:00Z'
                message: Adapter created successfully
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
        '413':
          description: JSON 请求体超过默认限制（通常为 2 MiB）。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to buffer the request body: length limit exceeded'
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize the JSON body: EOF while parsing a value'
        '422':
          description: JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。
          content:
            text/plain:
              schema:
                type: string
              example: Failed to deserialize the JSON body into the target type
        '415':
          description: JSON 请求缺少或使用了错误的 Content-Type。
          content:
            text/plain:
              schema:
                type: string
              example: 'Expected request with `Content-Type: application/json`'
      x-source-handler: collection_handlers::create_adapter
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateAdapter'
            example: &id051
              id: adapter_example
              name: 示例适配器
              script_file: sina_production
              source_id: source_example
              topic_name: corn_spot_price
  /api/adapters/{id}:
    get:
      operationId: get_adapter
      tags:
      - Adapters
      summary: 查询单个适配器
      description: 查询单个适配器
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/AdapterWithSource'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: *id002
                message: null
        '404':
          description: 资源不存在。 空响应体。
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
      x-source-handler: collection_handlers::get_adapter
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema:
          type: string
        example: adapter_sina_spot
    put:
      operationId: update_adapter
      tags:
      - Adapters
      summary: 修改适配器
      description: 部分更新；null 与未提供字段都不修改。仅 name/script_file/topic_name 可更新。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/Adapter'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: *id003
                message: Adapter updated successfully
        '404':
          description: 资源不存在。 空响应体。
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
        '413':
          description: JSON 请求体超过默认限制（通常为 2 MiB）。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to buffer the request body: length limit exceeded'
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize the JSON body: EOF while parsing a value'
        '422':
          description: JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。
          content:
            text/plain:
              schema:
                type: string
              example: Failed to deserialize the JSON body into the target type
        '415':
          description: JSON 请求缺少或使用了错误的 Content-Type。
          content:
            text/plain:
              schema:
                type: string
              example: 'Expected request with `Content-Type: application/json`'
      x-source-handler: collection_handlers::update_adapter
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema:
          type: string
        example: adapter_sina_spot
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UpdateAdapter'
            example: &id052
              name: 更新后的适配器名称
    delete:
      operationId: delete_adapter
      tags:
      - Adapters
      summary: 删除适配器
      description: 资源不存在也成功。可能级联删除关联记录/运行历史；async_jobs 外键限制可能导致 500。生产调用前确认依赖和备份。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: string
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: Adapter deleted successfully
                message: null
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
      x-source-handler: collection_handlers::delete_adapter
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema:
          type: string
        example: adapter_sina_spot
  /api/adapters/{id}/run:
    post:
      operationId: run_adapter
      tags:
      - Adapters
      summary: 后台执行适配器
      description: 创建 collection_runs 后后台执行，立即返回 HTTP 200 和 run_id。固定 max_items=100；不是 async_jobs，不返回 job_id。轮询
        /api/adapters/{id}/runs；本端点未防止重复并发提交。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/AdapterRunAccepted'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: &id043
                  run_id: f55ce408-550f-400a-8a03-94839115ac6a
                  status: running
                  message: 'Collection started for adapter: 新浪玉米现货'
                message: null
        '404':
          description: 资源不存在。 空响应体。
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
      x-source-handler: collection_handlers::run_adapter
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema:
          type: string
        example: adapter_sina_spot
  /api/adapters/{id}/start:
    post:
      operationId: start_adapter
      tags:
      - Adapters
      summary: 设置适配器为running
      description: 仅更新数据库状态；不会启动/停止 Python 进程，不会创建/取消定时任务，也不会中止正在运行的采集。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/Adapter'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data:
                  id: adapter_sina_spot
                  name: 新浪玉米现货
                  script_file: sina_production
                  source_id: source_sina
                  topic_name: corn_spot_price
                  status: running
                  last_run_at: null
                  last_cursor: null
                  total_runs: 0
                  successful_runs: 0
                  failed_runs: 0
                  last_error: null
                  created_at: '2026-10-22T01:00:00Z'
                  updated_at: '2026-10-22T01:00:00Z'
                message: Adapter started
        '404':
          description: 资源不存在。 空响应体。
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
      x-source-handler: collection_handlers::start_adapter
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema:
          type: string
        example: adapter_sina_spot
  /api/adapters/{id}/stop:
    post:
      operationId: stop_adapter
      tags:
      - Adapters
      summary: 设置适配器为stopped
      description: 仅更新数据库状态；不会启动/停止 Python 进程，不会创建/取消定时任务，也不会中止正在运行的采集。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/Adapter'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data:
                  id: adapter_sina_spot
                  name: 新浪玉米现货
                  script_file: sina_production
                  source_id: source_sina
                  topic_name: corn_spot_price
                  status: stopped
                  last_run_at: null
                  last_cursor: null
                  total_runs: 0
                  successful_runs: 0
                  failed_runs: 0
                  last_error: null
                  created_at: '2026-10-22T01:00:00Z'
                  updated_at: '2026-10-22T01:00:00Z'
                message: Adapter stopped
        '404':
          description: 资源不存在。 空响应体。
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
      x-source-handler: collection_handlers::stop_adapter
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema:
          type: string
        example: adapter_sina_spot
  /api/adapters/{id}/runs:
    get:
      operationId: get_adapter_runs
      tags:
      - Adapters
      summary: 适配器运行历史
      description: 验证适配器存在；started_at DESC、id DESC；仅数组，无总数。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/CollectionRun'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data:
                - &id025
                  id: f55ce408-550f-400a-8a03-94839115ac6a
                  adapter_id: adapter_sina_spot
                  started_at: '2026-10-22T01:00:00Z'
                  completed_at: '2026-10-22T01:00:20Z'
                  status: success
                  new_records: 1
                  duplicate_records: 0
                  failed_records: 0
                  start_cursor: null
                  end_cursor: '2026-10-22'
                  error_message: null
                  records_collected: 1
                message: null
        '400':
          description: 参数非法或调度操作失败。 空响应体。 Axum 提取失败时为 text/plain。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
        '404':
          description: 资源不存在。 空响应体。
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
      x-source-handler: collection_handlers::get_adapter_runs
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema:
          type: string
        example: adapter_sina_spot
      - name: limit
        in: query
        required: false
        description: 返回条数，u64。
        schema:
          type: integer
          default: 20
          minimum: 1
          maximum: 100
        example: 20
      - name: offset
        in: query
        required: false
        description: 跳过条数，u64；未显式验证 PostgreSQL int64 上界。
        schema:
          type: integer
          default: 0
          minimum: 0
        example: 0
  /api/adapters/{id}/records:
    get:
      operationId: get_adapter_records
      tags:
      - Adapters
      summary: 适配器采集记录
      description: 查询 collection_records，business_date DESC；保留企业/合约维度。适配器不存在返回空数组而非 404。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/CollectionRecord'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data:
                - &id004
                  id: f55ce408-550f-400a-8a03-94839115ac6a
                  adapter_id: adapter_sina_spot
                  business_date: '2026-10-22'
                  value: '2040.0000'
                  unit: 元/吨
                  topic_name: corn_spot_price
                  record_key: sina:example-processor:2026-10-22
                  indicator: 玉米现货价格
                  region: 山东
                  metadata:
                    enterprise: 示例企业（非实测数据）
                  source_url: https://finance.sina.com.cn/money/future/C/
                  source_html_path: null
                  quality_grade: B
                  quality_score: null
                  collected_at: '2026-10-22T01:00:00Z'
                  created_at: '2026-10-22T01:00:00Z'
                message: null
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
      x-source-handler: collection_handlers::get_adapter_records
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema:
          type: string
        example: adapter_sina_spot
      - name: limit
        in: query
        required: false
        description: u64；没有显式上限，建议小批量查询。
        schema:
          type: integer
          default: 50
          minimum: 0
        example: 1
  /api/topics:
    get:
      operationId: list_topics
      tags:
      - Topics
      summary: 主题列表
      description: 按适配器 topic_name 分组，按名称排序。record_count 恒为 0、latest_date 恒为 null（尚未实现真实统计）。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/TopicInfo'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data:
                - &id026
                  name: corn_spot_price
                  adapter_count: 1
                  record_count: 0
                  latest_date: null
                message: null
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
      x-source-handler: collection_handlers::list_topics
  /api/topics/{name}:
    get:
      operationId: get_topic
      tags:
      - Topics
      summary: 主题详情
      description: 未知主题返回 200，adapters=[]、record_count=0。record_count 查询错误也被降级为 0，不能据此判断数据库健康。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/TopicDetail'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: &id027
                  name: corn_spot_price
                  adapters:
                  - *id002
                  record_count: 1
                message: null
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
      x-source-handler: collection_handlers::get_topic
      parameters:
      - name: name
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema:
          type: string
        example: corn_spot_price
  /api/topics/{name}/records:
    get:
      operationId: get_topic_records
      tags:
      - Topics
      summary: 按主题查询采集记录
      description: collection_records.topic_name 精确匹配，business_date DESC。日期参数未生效。未知主题返回 []。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/CollectionRecord'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data:
                - *id004
                message: null
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
      x-source-handler: collection_handlers::get_topic_records
      parameters:
      - name: name
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema:
          type: string
        example: corn_spot_price
      - &id005
        name: start_date
        in: query
        required: false
        description: 当前被接受但未用于 SQL 过滤；不要依赖此参数。
        schema:
          type: string
        example: '2026-10-22'
      - &id006
        name: end_date
        in: query
        required: false
        description: 当前被接受但未用于 SQL 过滤；不要依赖此参数。
        schema:
          type: string
        example: '2026-10-22'
      - name: limit
        in: query
        required: false
        description: u64，无显式上限。
        schema:
          type: integer
          default: 100
          minimum: 0
        example: 1
  /api/records:
    get:
      operationId: query_records
      tags:
      - Records
      summary: 兼容原始记录查询
      description: 查询 raw_collection_records 后映射成 CollectionRecord；不保留完整企业/合约元数据。record_key=""，indicator/metadata/quality_*
        等为 null。按业务日期、采集时间降序。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/CollectionRecord'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data:
                - id: f55ce408-550f-400a-8a03-94839115ac6a
                  adapter_id: sina_production
                  business_date: '2026-10-22'
                  value: '2040.0000'
                  unit: 元/吨
                  topic_name: 玉米现货价格
                  record_key: ''
                  indicator: null
                  region: 山东
                  metadata: null
                  source_url: https://finance.sina.com.cn/money/future/C/
                  source_html_path: null
                  quality_grade: null
                  quality_score: null
                  collected_at: '2026-10-22T01:00:00Z'
                  created_at: '2026-10-22T01:00:00Z'
                message: null
        '500':
          description: 数据库、采集器或内部错误。 空响应体。
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
      x-source-handler: collection_handlers::query_records
      parameters:
      - name: adapter_id
        in: query
        required: false
        description: 实际过滤 raw_collection_records.collector_id，不是 adapters.id。
        schema:
          type: string
        example: sina_production
      - name: topic
        in: query
        required: false
        description: 实际精确过滤原始 indicator_name；不支持 topic 别名映射。
        schema:
          type: string
        example: 玉米现货价格
      - *id005
      - *id006
      - name: quality
        in: query
        required: false
        description: 被接受但未生效。
        schema:
          type: string
        example: B
      - name: limit
        in: query
        required: false
        description: u64，无显式上限。
        schema:
          type: integer
          default: 100
          minimum: 0
        example: 1
  /api/collectors:
    get:
      operationId: list_collectors
      tags:
      - Collectors
      summary: 采集器列表（静态）
      description: 当前工作树硬编码 boyar/sina/dce。status/counters/timestamps 为占位，不反映运行状态；DCE 在旧镜像中可能尚未部署。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/CollectorInfo'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data:
                - id: boyar
                  name: 博亚和讯
                  status: idle
                  last_run: null
                  last_success: null
                  total_runs: 0
                  success_rate: 0.0
                - &id028
                  id: sina
                  name: 新浪财经
                  status: idle
                  last_run: null
                  last_success: null
                  total_runs: 0
                  success_rate: 0.0
                - id: dce
                  name: 大连商品交易所
                  status: idle
                  last_run: null
                  last_success: null
                  total_runs: 0
                  success_rate: 0.0
                message: null
      x-source-handler: handlers::list_collectors
  /api/collectors/run:
    post:
      operationId: run_collector_by_name
      tags:
      - Collectors
      summary: 按名称同步采集
      description: 同步等待 Python 完成，可能耗时数分钟。长任务建议使用 /api/collectors/run/async。名称需在 runner 中注册，并唯一映射到适配器；boyar/sina/dce
        支持对应 *_production 别名。当前同步入口仅新浪/DCE 执行持久化；旧 Boyar/mock/cft 分支不保证写库或提交游标。返回计数不等于新增入库数，重复/无新数据可为 0。来源可用性取决于外部站点，不承诺固定条数。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/CollectorResult'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: &id007
                  collector_id: sina_production
                  records_collected: 1
                  run_id: f55ce408-550f-400a-8a03-94839115ac6a
                message: Collected 1 records
        '400':
          description: 参数非法或调度操作失败。
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CornError'
              example:
                success: false
                error: collector_name must not be empty
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize the JSON body: EOF while parsing a value'
        '500':
          description: 数据库、采集器或内部错误。
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CornError'
              example:
                success: false
                error: 'Internal error: Database query failed'
        '413':
          description: JSON 请求体超过默认限制（通常为 2 MiB）。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to buffer the request body: length limit exceeded'
        '422':
          description: JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。
          content:
            text/plain:
              schema:
                type: string
              example: Failed to deserialize the JSON body into the target type
        '415':
          description: JSON 请求缺少或使用了错误的 Content-Type。
          content:
            text/plain:
              schema:
                type: string
              example: 'Expected request with `Content-Type: application/json`'
      x-source-handler: handlers::run_collector_by_name
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/RunCollector'
            example: &id053
              collector_name: sina_production
              max_items: 100
  /api/collectors/{id}/run:
    post:
      operationId: run_collector
      tags:
      - Collectors
      summary: 按路径名称同步采集
      description: 固定 max_items=100，不读取请求体。同步等待 Python 完成，可能耗时数分钟。长任务建议使用 /api/collectors/run/async。名称需在 runner
        中注册，并唯一映射到适配器；boyar/sina/dce 支持对应 *_production 别名。当前同步入口仅新浪/DCE 执行持久化；旧 Boyar/mock/cft 分支不保证写库或提交游标。返回计数不等于新增入库数，重复/无新数据可为
        0。来源可用性取决于外部站点，不承诺固定条数。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/CollectorResult'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: *id007
                message: Collected 1 records
        '400':
          description: 参数非法或调度操作失败。
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CornError'
              example:
                success: false
                error: 'Unknown collector: missing_collector'
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
        '500':
          description: 数据库、采集器或内部错误。
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CornError'
              example:
                success: false
                error: 'Internal error: Database query failed'
      x-source-handler: handlers::run_collector
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema:
          type: string
        example: sina_production
  /api/collectors/{id}/history:
    get:
      operationId: get_collector_history
      tags:
      - Collectors
      summary: 采集器历史
      description: 按 started_at DESC、id DESC。未知/歧义采集器映射返回 400，而非 404。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/CollectionHistory'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data:
                - &id029
                  id: f55ce408-550f-400a-8a03-94839115ac6a
                  collector_id: sina_production
                  started_at: '2026-10-22T01:00:00Z'
                  completed_at: '2026-10-22T01:00:20Z'
                  status: success
                  records_collected: 1
                  error_message: null
                message: null
        '400':
          description: 参数非法或调度操作失败。
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CornError'
              example:
                success: false
                error: limit must be between 1 and 100
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
        '500':
          description: 数据库、采集器或内部错误。
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CornError'
              example:
                success: false
                error: 'Internal error: Database query failed'
      x-source-handler: handlers::get_collector_history
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema:
          type: string
        example: sina_production
      - name: limit
        in: query
        required: false
        description: 1..100，默认 50。
        schema:
          type: integer
          default: 50
          minimum: 1
          maximum: 100
        example: 10
  /api/collectors/{id}/status:
    get:
      operationId: get_collector_status
      tags:
      - Collectors
      summary: 采集器状态（占位）
      description: 任意 id 都返回 idle、计数 0、时间 null；未验证采集器存在。查询真实执行状态请用 jobs 或 runs。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/CollectorInfo'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data:
                  id: sina_production
                  name: sina_production
                  status: idle
                  last_run: null
                  last_success: null
                  total_runs: 0
                  success_rate: 0.0
                message: null
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
      x-source-handler: handlers::get_collector_status
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema:
          type: string
        example: sina_production
  /api/collectors/run/async:
    post:
      operationId: submit
      tags:
      - AsyncJobs
      summary: 提交持久化后台采集
      description: 立即返回 job_id。每适配器最多一个 queued/running 的异步任务，重复提交 409。PostgreSQL 队列由两个后台 worker 轮询；queued 可恢复，重启时未完成
        running 通常标失败（已提交成功的关联 run 可恢复成功）。Python 超时 2 小时；没有取消/重放接口。
      responses:
        '202':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/AsyncJobAccepted'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: &id044
                  job_id: f55ce408-550f-400a-8a03-94839115ac6a
                  status: queued
                  status_url: /api/jobs/f55ce408-550f-400a-8a03-94839115ac6a
                message: Collection queued
        '400':
          description: 参数非法或调度操作失败。
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CornError'
              example:
                success: false
                error: collector_name is required; max_items must be 1..1000
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize the JSON body: EOF while parsing a value'
        '409':
          description: 存在运行中的任务，或状态冲突。
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CornError'
              example:
                success: false
                error: An async collection is already queued/running for this adapter
        '500':
          description: 数据库、采集器或内部错误。
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CornError'
              example:
                success: false
                error: 'Internal error: Database query failed'
        '413':
          description: JSON 请求体超过默认限制（通常为 2 MiB）。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to buffer the request body: length limit exceeded'
        '422':
          description: JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。
          content:
            text/plain:
              schema:
                type: string
              example: Failed to deserialize the JSON body into the target type
        '415':
          description: JSON 请求缺少或使用了错误的 Content-Type。
          content:
            text/plain:
              schema:
                type: string
              example: 'Expected request with `Content-Type: application/json`'
      x-source-handler: async_jobs::submit
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SubmitAsyncJob'
            example: &id054
              collector_name: boyar_production
              max_items: 100
  /api/jobs/{id}:
    get:
      operationId: get
      tags:
      - AsyncJobs
      summary: 查询后台任务
      description: job_id 必须 UUID。状态 queued → running → succeeded/failed；仅成功任务进度 100。progress 为阶段进度，不是时间估计；result
        成功时通常含 records_collected。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/AsyncJob'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: &id038
                  id: f55ce408-550f-400a-8a03-94839115ac6a
                  collector_name: boyar_production
                  adapter_id: adapter_boyar_shandong
                  run_id: null
                  max_items: 100
                  status: queued
                  progress: 0
                  phase: queued
                  details: {}
                  result: null
                  error_message: null
                  created_at: '2026-10-22T01:00:00Z'
                  started_at: null
                  completed_at: null
                  updated_at: '2026-10-22T01:00:00Z'
                message: null
        '404':
          description: 资源不存在。
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CornError'
              example:
                success: false
                error: Async job not found
        '500':
          description: 数据库、采集器或内部错误。
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CornError'
              example:
                success: false
                error: 'Internal error: Database query failed'
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Invalid URL: Cannot parse UUID'
      x-source-handler: async_jobs::get
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema: &id009
          type: string
          description: UUID。
          format: uuid
        example: f55ce408-550f-400a-8a03-94839115ac6a
  /api/data/latest:
    get:
      operationId: get_latest_data
      tags:
      - Data
      summary: 最新市场数据
      description: 读取 raw_collection_records；business_date DESC、collected_at DESC。value 是 number，quality 固定为 A，缺失企业/合约
        provenance；需要精确来源请查适配器 records。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/MarketData'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data:
                - &id008
                  id: f55ce408-550f-400a-8a03-94839115ac6a
                  business_date: '2026-10-22'
                  indicator_name: 玉米现货价格
                  value: 2040.0
                  unit: 元/吨
                  source: sina_production
                  quality: A
                  collected_at: '2026-10-22T01:00:00Z'
                message: null
        '400':
          description: 参数非法或调度操作失败。
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CornError'
              example:
                success: false
                error: days must be 1..36500 and limit must be 1..10000
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
        '500':
          description: 数据库、采集器或内部错误。
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CornError'
              example:
                success: false
                error: 'Internal error: Database query failed'
      x-source-handler: handlers::get_latest_data
      parameters:
      - name: topic
        in: query
        required: false
        description: 主题映射见通用说明；未知值按 indicator_name 精确过滤。
        schema:
          type: string
        example: corn_spot_price
      - name: indicator
        in: query
        required: false
        description: 指标名精确过滤；与 topic 为 AND 关系。
        schema:
          type: string
        example: 玉米现货价格
      - name: days
        in: query
        required: false
        description: 以 UTC 今日为上界、今日减 days 为下界，两端均包含。
        schema:
          type: integer
          default: 30
          minimum: 1
          maximum: 36500
        example: 30
      - name: limit
        in: query
        required: false
        description: 最大返回条数。
        schema:
          type: integer
          default: 100
          minimum: 1
          maximum: 10000
        example: 1
  /api/data/stats:
    get:
      operationId: get_stats
      tags:
      - Data
      summary: 原始数据统计
      description: 统计原始记录。coverage_rate 为占位 85.5/0；当前实现读取全部原始记录进行指标聚合，大数据量时需注意成本。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/DataStats'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: &id031
                  total_records: 1
                  indicator_count: 1
                  coverage_rate: 85.5
                  latest_collection: '2026-10-22T01:00:00Z'
                message: null
        '500':
          description: 数据库、采集器或内部错误。
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CornError'
              example:
                success: false
                error: 'Internal error: Database query failed'
      x-source-handler: handlers::get_stats
  /api/data/trend:
    get:
      operationId: get_trend_data
      tags:
      - Data
      summary: 指标趋势
      description: 按 business_date ASC；不聚合、不按企业/合约区分、不提供 limit。quality 固定 A。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/MarketData'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data:
                - *id008
                message: null
        '400':
          description: 参数非法或调度操作失败。
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CornError'
              example:
                success: false
                error: days must be 1..36500
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
        '500':
          description: 数据库、采集器或内部错误。
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CornError'
              example:
                success: false
                error: 'Internal error: Database query failed'
      x-source-handler: handlers::get_trend_data
      parameters:
      - name: indicator
        in: query
        required: true
        description: 必需，指标名精确匹配。
        schema:
          type: string
        example: 玉米现货价格
      - name: days
        in: query
        required: false
        description: UTC 日期窗口，含两端。
        schema:
          type: integer
          default: 30
          minimum: 1
          maximum: 36500
        example: 7
  /api/data/indicators:
    get:
      operationId: get_indicators
      tags:
      - Data
      summary: 指标列表
      description: 扫描全部 raw 记录分组；display_name=name；顺序不保证。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/IndicatorInfo'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data:
                - &id032
                  name: 玉米现货价格
                  display_name: 玉米现货价格
                  unit: 元/吨
                  record_count: 1
                message: null
        '500':
          description: 数据库、采集器或内部错误。
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CornError'
              example:
                success: false
                error: 'Internal error: Database query failed'
      x-source-handler: handlers::get_indicators
  /api/quality/scores:
    get:
      operationId: get_quality_scores
      tags:
      - Quality
      summary: 质量分数（占位）
      description: 当前固定返回空数组，尚未执行质量评分。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/QualityScore'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: []
                message: null
      x-source-handler: handlers::get_quality_scores
  /api/quality/distribution:
    get:
      operationId: get_quality_distribution
      tags:
      - Quality
      summary: 质量分布（占位）
      description: 当前固定全零，grade_m 表示 Mock 测试数据类别，不是生产统计。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/QualityDistribution'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: &id033
                  grade_a: 0
                  grade_b: 0
                  grade_c: 0
                  grade_d: 0
                  grade_m: 0
                message: 质量分布统计(M=Mock测试数据)
      x-source-handler: handlers::get_quality_distribution
  /api/quality/issues:
    get:
      operationId: get_quality_issues
      tags:
      - Quality
      summary: 问题数据（占位）
      description: 当前固定空数组；未读取 severity 等过滤参数。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/MarketData'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: []
                message: null
      x-source-handler: handlers::get_quality_issues
  /api/data/{id}/lineage:
    get:
      operationId: get_data_lineage
      tags:
      - Lineage
      summary: 标准记录血统
      description: id 是 STANDARD 表记录 UUID（不是 raw id）。无效 UUID、记录不存在或数据库错误均返回 HTTP 200 + success:false。关联原始记录查询失败也可能降级为
        raw_record:null。
      responses:
        '200':
          description: HTTP 200 可能包含 success:false，客户端必须检查响应体。
          content:
            application/json:
              schema:
                oneOf:
                - type: object
                  properties:
                    success:
                      type: boolean
                      enum:
                      - true
                    data:
                      $ref: '#/components/schemas/Lineage'
                    message:
                      type: string
                      nullable: true
                  required:
                  - success
                  - data
                  - message
                - $ref: '#/components/schemas/ApplicationFailure'
              examples:
                success:
                  value:
                    success: true
                    data: &id042
                      standard_record: &id041
                        id: ba3c20b5-b049-48d1-9942-d5b04fa7f9ac
                        business_date: '2026-10-22'
                        indicator_name: 玉米现货价格
                        value: '2040.0000'
                        unit: 元/吨
                        region: 山东
                        quality_grade: B
                        quality_score: '90.00'
                        quality_issues: null
                        source_id: sina_production
                        raw_record_id: f55ce408-550f-400a-8a03-94839115ac6a
                        collected_at: '2026-10-22T01:00:00Z'
                        standardized_at: '2026-10-22T01:00:00Z'
                        version: 1
                        is_latest: true
                        metadata: null
                        created_at: '2026-10-22T01:00:00Z'
                        updated_at: '2026-10-22T01:00:00Z'
                      raw_record: &id039
                        id: f55ce408-550f-400a-8a03-94839115ac6a
                        collector_id: sina_production
                        business_date: '2026-10-22'
                        indicator_name: 玉米现货价格
                        value: '2040.0000'
                        unit: 元/吨
                        region: 山东
                        source_url: https://finance.sina.com.cn/money/future/C/
                        original_text: null
                        dedup_key: example-key
                        collected_at: '2026-10-22T01:00:00Z'
                        created_at: '2026-10-22T01:00:00Z'
                        updated_at: '2026-10-22T01:00:00Z'
                      lineage_chain:
                      - '原始记录: example-key'
                      - '采集: sina_production (2026-10-22 01:00)'
                      - '标准化: 2026-10-22 01:00 (质量等级: B)'
                      - '版本: 1'
                    message: null
                application_failure:
                  value:
                    success: false
                    data: null
                    message: Record not found
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
      x-source-handler: get_data_lineage
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema:
          type: string
        example: f55ce408-550f-400a-8a03-94839115ac6a
  /api/data/standardize:
    post:
      operationId: trigger_standardization
      tags:
      - Lineage
      summary: 批量标准化
      description: raw_record_ids 必须数组。逐项处理，UUID 无效、未找到或标准化失败计入 error_count；即便全部失败也 HTTP 200 且 success:true。不限制数组长度。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/StandardizationResult'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: &id047
                  success_count: 1
                  error_count: 0
                message: Standardized 1 records
        '413':
          description: JSON 请求体超过默认限制（通常为 2 MiB）。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to buffer the request body: length limit exceeded'
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize the JSON body: EOF while parsing a value'
        '422':
          description: JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。
          content:
            text/plain:
              schema:
                type: string
              example: Failed to deserialize the JSON body into the target type
        '415':
          description: JSON 请求缺少或使用了错误的 Content-Type。
          content:
            text/plain:
              schema:
                type: string
              example: 'Expected request with `Content-Type: application/json`'
      x-source-handler: trigger_standardization
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Standardize'
            example: &id055
              raw_record_ids:
              - f55ce408-550f-400a-8a03-94839115ac6a
  /api/data/auto-promote:
    post:
      operationId: trigger_auto_promotion
      tags:
      - Lineage
      summary: 自动提升合格原始数据
      description: 不读取请求体；尝试提升最近 24 小时符合 A/B 质量要求、尚未提升的原始记录。业务失败仍返回 HTTP 200，需检查 success。
      responses:
        '200':
          description: HTTP 200 可能包含 success:false，客户端必须检查响应体。
          content:
            application/json:
              schema:
                oneOf:
                - type: object
                  properties:
                    success:
                      type: boolean
                      enum:
                      - true
                    data:
                      $ref: '#/components/schemas/PromotionResult'
                    message:
                      type: string
                      nullable: true
                  required:
                  - success
                  - data
                  - message
                - type: object
                  properties:
                    success:
                      type: boolean
                      enum:
                      - false
                    data:
                      $ref: '#/components/schemas/PromotionResult'
                    message:
                      type: string
                  required:
                  - success
                  - data
                  - message
              examples:
                success:
                  value:
                    success: true
                    data: &id048
                      promoted_count: 1
                    message: Auto-promoted 1 records
                application_failure:
                  value:
                    success: false
                    data:
                      promoted_count: 0
                    message: 'Auto-promotion failed: Database error'
      x-source-handler: trigger_auto_promotion
  /api/notifications:
    get:
      operationId: get_notifications
      tags:
      - Notifications
      summary: 通知历史
      description: 从 Redis 读取最新优先通知；Redis 列表最多保留 100 条。metadata 没有值时省略。Redis 错误 HTTP 200 + success:false。无用户隔离。
      responses:
        '200':
          description: HTTP 200 可能包含 success:false，客户端必须检查响应体。
          content:
            application/json:
              schema:
                oneOf:
                - type: object
                  properties:
                    success:
                      type: boolean
                      enum:
                      - true
                    data:
                      type: array
                      items:
                        $ref: '#/components/schemas/Notification'
                    message:
                      type: string
                      nullable: true
                  required:
                  - success
                  - data
                  - message
                - $ref: '#/components/schemas/ApplicationFailure'
              examples:
                success:
                  value:
                    success: true
                    data:
                    - &id035
                      id: f55ce408-550f-400a-8a03-94839115ac6a
                      level: error
                      title: 定时采集失败
                      message: 示例错误：数据源请求失败
                      timestamp: '2026-10-22T01:00:00Z'
                    message: null
                application_failure:
                  value:
                    success: false
                    data: null
                    message: Redis operation failed
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
      x-source-handler: get_notifications
      parameters:
      - name: limit
        in: query
        required: false
        description: usize，默认 50。未显式校验上限；请使用 1..100。0 存在 limit-1 下溢风险，并非稳定的空列表语义。
        schema:
          type: integer
          default: 50
          minimum: 0
        example: 10
  /api/notifications/mark-read:
    post:
      operationId: mark_notification_read
      tags:
      - Notifications
      summary: 通知标为已读
      description: 添加全局 Redis 已读集合；不验证通知存在，不按用户区分，历史查询不返回已读状态。Redis 失败仍 HTTP 200。
      responses:
        '200':
          description: HTTP 200 可能包含 success:false，客户端必须检查响应体。
          content:
            application/json:
              schema:
                oneOf:
                - type: object
                  properties:
                    success:
                      type: boolean
                      enum:
                      - true
                    data:
                      type: string
                    message:
                      type: string
                      nullable: true
                  required:
                  - success
                  - data
                  - message
                - $ref: '#/components/schemas/ApplicationFailure'
              examples:
                success:
                  value:
                    success: true
                    data: Notification marked as read
                    message: null
                application_failure:
                  value:
                    success: false
                    data: null
                    message: Redis operation failed
        '413':
          description: JSON 请求体超过默认限制（通常为 2 MiB）。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to buffer the request body: length limit exceeded'
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize the JSON body: EOF while parsing a value'
        '422':
          description: JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。
          content:
            text/plain:
              schema:
                type: string
              example: Failed to deserialize the JSON body into the target type
        '415':
          description: JSON 请求缺少或使用了错误的 Content-Type。
          content:
            text/plain:
              schema:
                type: string
              example: 'Expected request with `Content-Type: application/json`'
      x-source-handler: mark_notification_read
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MarkRead'
            example: &id056
              notification_id: f55ce408-550f-400a-8a03-94839115ac6a
  /api/scheduler/jobs:
    get:
      operationId: list_jobs
      tags:
      - Scheduler
      summary: 调度任务列表
      description: created_at ASC、id ASC；next_run 可能为 null，不代表自动调度已验证。错误通常是 text/plain，不是 CornError JSON；部分数据库错误当前也映射为
        400。Cron 使用 UTC 六字段（含秒）；北京时间 08:00 为 0 0 0 * * *，09:00 为 0 0 1 * * *。未实现自动失败重试或停机补跑。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/ScheduledJob'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data:
                - &id036
                  id: f55ce408-550f-400a-8a03-94839115ac6a
                  name: 新浪每日09:00
                  collector_id: sina_production
                  cron_expression: 0 0 1 * * *
                  enabled: true
                  description: null
                  status: idle
                  last_run: null
                  last_error: null
                  total_runs: 0
                  success_count: 0
                  failed_count: 0
                  created_at: '2026-10-22T01:00:00Z'
                  next_run: '2026-10-22T01:00:00Z'
                  timezone: UTC
                message: null
        '400':
          description: 参数非法或调度操作失败。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize query string: invalid digit found in string'
        '500':
          description: 数据库、采集器或内部错误。
          content:
            text/plain:
              schema:
                type: string
              example: Response serialization failed
      x-source-handler: list_jobs
    post:
      operationId: create_job
      tags:
      - Scheduler
      summary: 创建调度任务
      description: 名称不可为空，Cron 校验并验证适配器映射；enabled 默认 true；成功 HTTP 200。错误通常是 text/plain，不是 CornError JSON；部分数据库错误当前也映射为
        400。Cron 使用 UTC 六字段（含秒）；北京时间 08:00 为 0 0 0 * * *，09:00 为 0 0 1 * * *。未实现自动失败重试或停机补跑。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/ScheduleCreated'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: &id045
                  job_id: f55ce408-550f-400a-8a03-94839115ac6a
                message: null
        '400':
          description: 参数非法或调度操作失败。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize the JSON body: EOF while parsing a value'
        '500':
          description: 数据库、采集器或内部错误。
          content:
            text/plain:
              schema:
                type: string
              example: Response serialization failed
        '413':
          description: JSON 请求体超过默认限制（通常为 2 MiB）。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to buffer the request body: length limit exceeded'
        '422':
          description: JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。
          content:
            text/plain:
              schema:
                type: string
              example: Failed to deserialize the JSON body into the target type
        '415':
          description: JSON 请求缺少或使用了错误的 Content-Type。
          content:
            text/plain:
              schema:
                type: string
              example: 'Expected request with `Content-Type: application/json`'
      x-source-handler: create_job
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateSchedule'
            example: &id057
              name: 新浪每日09:00
              collector_id: sina_production
              cron_expression: 0 0 1 * * *
              description: 北京时间每日09:00采集
              enabled: true
  /api/scheduler/jobs/{id}:
    post:
      operationId: trigger_job
      tags:
      - Scheduler
      summary: 手动触发调度任务
      description: 创建 job_executions 后后台执行。手动允许触发 disabled 任务；同任务运行时拒绝。不存在/禁用/已运行的共用错误消息映射为 409，因此未知 UUID 也可能是 409（不是
        404）。POST 成功不代表采集已成功，请轮询 executions；错误原因写 error_message。错误通常是 text/plain，不是 CornError JSON；部分数据库错误当前也映射为
        400。Cron 使用 UTC 六字段（含秒）；北京时间 08:00 为 0 0 0 * * *，09:00 为 0 0 1 * * *。未实现自动失败重试或停机补跑。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    $ref: '#/components/schemas/ScheduleTriggered'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: &id046
                  execution_id: f55ce408-550f-400a-8a03-94839115ac6a
                  status: running
                message: null
        '400':
          description: 参数非法或调度操作失败。
          content:
            text/plain:
              schema:
                type: string
              example: 'Invalid URL: Cannot parse UUID'
        '409':
          description: 存在运行中的任务，或状态冲突。
          content:
            text/plain:
              schema:
                type: string
              example: Job not found, disabled, or already running
        '500':
          description: 数据库、采集器或内部错误。
          content:
            text/plain:
              schema:
                type: string
              example: Response serialization failed
      x-source-handler: trigger_job
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema: *id009
        example: f55ce408-550f-400a-8a03-94839115ac6a
    put:
      operationId: update_job
      tags:
      - Scheduler
      summary: 修改调度任务（未实现）
      description: 始终返回 501；请禁用/删除后重建。处理函数不解析路径 UUID，也不读取 JSON 请求体。
      responses:
        '501':
          description: 接口存在，但功能未实现。
          content:
            text/plain:
              schema:
                type: string
              example: Schedule editing is not supported; disable/delete and recreate the job
        '400':
          description: 路径/查询/JSON 语法解析失败（Axum）；处理函数也可能返回该状态。
          content:
            text/plain:
              schema:
                type: string
              example: 'Invalid URL: Cannot parse UUID'
      x-source-handler: update_job
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema:
          type: string
        example: adapter_sina_spot
    delete:
      operationId: delete_job
      tags:
      - Scheduler
      summary: 删除调度任务
      description: 正在执行时 409；不存在 404。删除同时级联清理执行历史。错误通常是 text/plain，不是 CornError JSON；部分数据库错误当前也映射为 400。Cron 使用 UTC
        六字段（含秒）；北京时间 08:00 为 0 0 0 * * *，09:00 为 0 0 1 * * *。未实现自动失败重试或停机补跑。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: string
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: Job deleted
                message: null
        '400':
          description: 参数非法或调度操作失败。
          content:
            text/plain:
              schema:
                type: string
              example: 'Invalid URL: Cannot parse UUID'
        '404':
          description: 资源不存在。
          content:
            text/plain:
              schema:
                type: string
              example: Job not found
        '409':
          description: 存在运行中的任务，或状态冲突。
          content:
            text/plain:
              schema:
                type: string
              example: Job is running
        '500':
          description: 数据库、采集器或内部错误。
          content:
            text/plain:
              schema:
                type: string
              example: Response serialization failed
      x-source-handler: delete_job
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema: *id009
        example: f55ce408-550f-400a-8a03-94839115ac6a
  /api/scheduler/jobs/{id}/enable:
    put:
      operationId: toggle_job
      tags:
      - Scheduler
      summary: 启用/停用调度任务
      description: 更新数据库及运行时注册；停用不会取消正在运行的采集。不存在返回 404。错误通常是 text/plain，不是 CornError JSON；部分数据库错误当前也映射为 400。Cron
        使用 UTC 六字段（含秒）；北京时间 08:00 为 0 0 0 * * *，09:00 为 0 0 1 * * *。未实现自动失败重试或停机补跑。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: string
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data: Job toggled
                message: null
        '400':
          description: 参数非法或调度操作失败。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to deserialize the JSON body: EOF while parsing a value'
        '404':
          description: 资源不存在。
          content:
            text/plain:
              schema:
                type: string
              example: Job not found
        '500':
          description: 数据库、采集器或内部错误。
          content:
            text/plain:
              schema:
                type: string
              example: Response serialization failed
        '413':
          description: JSON 请求体超过默认限制（通常为 2 MiB）。
          content:
            text/plain:
              schema:
                type: string
              example: 'Failed to buffer the request body: length limit exceeded'
        '422':
          description: JSON 字段缺失、类型不匹配，或 collector_name/collector_id 重复。
          content:
            text/plain:
              schema:
                type: string
              example: Failed to deserialize the JSON body into the target type
        '415':
          description: JSON 请求缺少或使用了错误的 Content-Type。
          content:
            text/plain:
              schema:
                type: string
              example: 'Expected request with `Content-Type: application/json`'
      x-source-handler: toggle_job
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema: *id009
        example: f55ce408-550f-400a-8a03-94839115ac6a
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ToggleSchedule'
            example: &id058
              enabled: false
  /api/scheduler/jobs/{id}/executions:
    get:
      operationId: get_job_executions
      tags:
      - Scheduler
      summary: 调度执行历史
      description: 按 started_at DESC、id DESC；无 total 字段。无任务时 404。错误通常是 text/plain，不是 CornError JSON；部分数据库错误当前也映射为
        400。Cron 使用 UTC 六字段（含秒）；北京时间 08:00 为 0 0 0 * * *，09:00 为 0 0 1 * * *。未实现自动失败重试或停机补跑。
      responses:
        '200':
          description: 成功。
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    enum:
                    - true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/JobExecution'
                  message:
                    type: string
                    nullable: true
                required:
                - success
                - data
                - message
              example:
                success: true
                data:
                - &id037
                  id: 7d723742-0d18-46fb-8025-61cb1903c647
                  job_id: f55ce408-550f-400a-8a03-94839115ac6a
                  trigger_type: manual
                  status: failed
                  started_at: '2026-10-22T01:00:00Z'
                  completed_at: '2026-10-22T01:00:01Z'
                  records_collected: 0
                  collection_run_id: null
                  error_message: 示例：数据源请求失败
                message: null
        '400':
          description: 参数非法或调度操作失败。
          content:
            text/plain:
              schema:
                type: string
              example: 'Invalid URL: Cannot parse UUID'
        '404':
          description: 资源不存在。
          content:
            text/plain:
              schema:
                type: string
              example: Job not found
        '500':
          description: 数据库、采集器或内部错误。
          content:
            text/plain:
              schema:
                type: string
              example: Response serialization failed
      x-source-handler: get_job_executions
      parameters:
      - name: id
        in: path
        required: true
        description: 路径标识；不是查询参数。
        schema: *id009
        example: f55ce408-550f-400a-8a03-94839115ac6a
      - name: limit
        in: query
        required: false
        description: 每页条数。
        schema:
          type: integer
          default: 20
          minimum: 1
          maximum: 100
        example: 20
      - name: offset
        in: query
        required: false
        description: 跳过条数，必须不超过 int64 最大值。
        schema:
          type: integer
          default: 0
          minimum: 0
          maximum: 9223372036854775807
        example: 0
      - name: status
        in: query
        required: false
        description: 精确匹配。
        schema:
          type: string
          enum:
          - running
          - success
          - failed
        example: failed
      - name: start_date
        in: query
        required: false
        description: started_at 下界，RFC 3339，含边界。URL 中 + 需转义为 %2B。
        schema:
          type: string
          format: date-time
        example: '2026-10-01T00:00:00Z'
      - name: end_date
        in: query
        required: false
        description: started_at 上界，RFC 3339，含边界；不得早于 start_date。
        schema:
          type: string
          format: date-time
        example: '2026-10-31T23:59:59Z'
components:
  schemas:
    Source:
      type: object
      properties:
        id:
          type: string
          description: 数据源标识，非强制 UUID。
        name:
          type: string
          description: 显示名称。
        domain:
          type: string
          description: 域名。
          nullable: true
        description:
          type: string
          description: 说明。
          nullable: true
        status:
          type: string
          description: 状态；创建时为 active。
        created_at:
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
        updated_at:
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
      required:
      - id
      - name
      - domain
      - description
      - status
      - created_at
      - updated_at
      example: *id001
    Adapter:
      type: object
      properties:
        id: &id010
          type: string
          description: 适配器标识。
        name: &id011
          type: string
          description: 显示名称。
        script_file: &id012
          type: string
          description: Python 采集器名称，不带 .py。
        source_id: &id013
          type: string
          description: 关联 sources.id。
        topic_name: &id014
          type: string
          description: 主题标识。
        status: &id015
          type: string
          description: 数据库状态，不代表实时进程状态。
        last_run_at: &id016
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
        last_cursor: &id017
          type: string
          description: 采集游标快照。
          nullable: true
        total_runs: &id018
          type: integer
        successful_runs: &id019
          type: integer
        failed_runs: &id020
          type: integer
        last_error: &id021
          type: string
          description: 最近错误。
          nullable: true
        created_at: &id022
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
        updated_at: &id023
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
      required:
      - id
      - name
      - script_file
      - source_id
      - topic_name
      - status
      - last_run_at
      - last_cursor
      - total_runs
      - successful_runs
      - failed_runs
      - last_error
      - created_at
      - updated_at
      example: *id003
    AdapterWithSource:
      type: object
      properties:
        id: *id010
        name: *id011
        script_file: *id012
        source_id: *id013
        topic_name: *id014
        status: *id015
        last_run_at: *id016
        last_cursor: *id017
        total_runs: *id018
        successful_runs: *id019
        failed_runs: *id020
        last_error: *id021
        created_at: *id022
        updated_at: *id023
        source:
          type: object
          properties:
            id:
              type: string
              description: 数据源标识，非强制 UUID。
            name:
              type: string
              description: 显示名称。
            domain:
              type: string
              description: 域名。
              nullable: true
            description:
              type: string
              description: 说明。
              nullable: true
            status:
              type: string
              description: 状态；创建时为 active。
            created_at:
              type: string
              description: RFC 3339 时间，包含时区。
              format: date-time
              nullable: true
            updated_at:
              type: string
              description: RFC 3339 时间，包含时区。
              format: date-time
              nullable: true
          required:
          - id
          - name
          - domain
          - description
          - status
          - created_at
          - updated_at
          example:
            id: source_sina
            name: 新浪财经
            domain: finance.sina.com.cn
            description: 玉米市场价格
            status: active
            created_at: '2026-10-22T01:00:00Z'
            updated_at: '2026-10-22T01:00:00Z'
          nullable: true
      required:
      - id
      - name
      - script_file
      - source_id
      - topic_name
      - status
      - last_run_at
      - last_cursor
      - total_runs
      - successful_runs
      - failed_runs
      - last_error
      - created_at
      - updated_at
      - source
      description: Adapter 字段平铺，source 为关联数据源，不存在嵌套 adapter 字段。
      example: *id002
    CollectionRecord:
      type: object
      properties:
        id:
          type: string
        adapter_id:
          type: string
        business_date: &id030
          type: string
          description: 业务日期，ISO 8601。
          format: date
        value:
          type: string
          description: 数据库 Decimal 以十进制字符串序列化，不能按 JSON number 处理。
          pattern: ^-?\d+(\.\d+)?$
          nullable: true
        unit:
          type: string
          nullable: true
        topic_name:
          type: string
          nullable: true
        record_key:
          type: string
          description: 企业/合约等序列的去重键。
        indicator:
          type: string
          nullable: true
        region:
          type: string
          nullable: true
        metadata: &id034
          description: 任意 JSON 值。
          nullable: true
        source_url:
          type: string
          nullable: true
        source_html_path:
          type: string
          nullable: true
        quality_grade:
          type: string
          nullable: true
        quality_score:
          type: integer
          nullable: true
        collected_at: &id024
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
        created_at:
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
      required:
      - id
      - adapter_id
      - business_date
      - value
      - unit
      - topic_name
      - record_key
      - indicator
      - region
      - metadata
      - source_url
      - source_html_path
      - quality_grade
      - quality_score
      - collected_at
      - created_at
      example: *id004
    CollectionRun:
      type: object
      properties:
        id:
          type: string
        adapter_id:
          type: string
        started_at: *id024
        completed_at:
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
        status:
          type: string
          description: 通常为 running/success/failed。
          nullable: true
        new_records:
          type: integer
          nullable: true
        duplicate_records:
          type: integer
          nullable: true
        failed_records:
          type: integer
          nullable: true
        start_cursor:
          type: string
          nullable: true
        end_cursor:
          type: string
          nullable: true
        error_message:
          type: string
          nullable: true
        records_collected:
          type: integer
      required:
      - id
      - adapter_id
      - started_at
      - completed_at
      - status
      - new_records
      - duplicate_records
      - failed_records
      - start_cursor
      - end_cursor
      - error_message
      - records_collected
      example: *id025
    TopicInfo:
      type: object
      properties:
        name:
          type: string
        adapter_count:
          type: integer
          minimum: 0
        record_count:
          type: integer
          description: 当前恒为 0（占位）。
          minimum: 0
        latest_date:
          type: string
          description: 当前恒为 null（占位）。
          nullable: true
      required:
      - name
      - adapter_count
      - record_count
      - latest_date
      example: *id026
    TopicDetail:
      type: object
      properties:
        name:
          type: string
        adapters:
          type: array
          items:
            $ref: '#/components/schemas/AdapterWithSource'
        record_count:
          type: integer
          minimum: 0
      required:
      - name
      - adapters
      - record_count
      example: *id027
    CollectorInfo:
      type: object
      properties:
        id:
          type: string
        name:
          type: string
        status:
          type: string
          enum:
          - idle
          - running
          - failed
        last_run:
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
        last_success:
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
        total_runs:
          type: integer
          minimum: 0
        success_rate:
          type: number
      required:
      - id
      - name
      - status
      - last_run
      - last_success
      - total_runs
      - success_rate
      description: 当前状态接口返回静态占位值，不用于判断真实任务是否运行。
      example: *id028
    CollectionHistory:
      type: object
      properties:
        id:
          type: string
        collector_id:
          type: string
        started_at: *id024
        completed_at:
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
        status:
          type: string
          description: 空状态转换为 unknown。
        records_collected:
          type: integer
          minimum: 0
        error_message:
          type: string
          nullable: true
      required:
      - id
      - collector_id
      - started_at
      - completed_at
      - status
      - records_collected
      - error_message
      example: *id029
    MarketData:
      type: object
      properties:
        id:
          type: string
        business_date: *id030
        indicator_name:
          type: string
        value:
          type: number
          description: 此接口为浮点数，与 CollectionRecord 的 Decimal 字符串不同。
        unit:
          type: string
        source:
          type: string
          description: 原始 collector_id，不是 sources.id。
        quality:
          type: string
          description: 当前固定为 A，不代表来源/质量评估结果。
        collected_at: *id024
      required:
      - id
      - business_date
      - indicator_name
      - value
      - unit
      - source
      - quality
      - collected_at
      example: *id008
    DataStats:
      type: object
      properties:
        total_records:
          type: integer
          minimum: 0
        indicator_count:
          type: integer
          minimum: 0
        coverage_rate:
          type: number
          description: 有指标时固定 85.5，无指标时 0，非真实覆盖率。
        latest_collection:
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
      required:
      - total_records
      - indicator_count
      - coverage_rate
      - latest_collection
      example: *id031
    IndicatorInfo:
      type: object
      properties:
        name:
          type: string
        display_name:
          type: string
          description: 当前与 name 相同。
        unit:
          type: string
        record_count:
          type: integer
          minimum: 0
      required:
      - name
      - display_name
      - unit
      - record_count
      example: *id032
    QualityScore:
      type: object
      properties:
        indicator:
          type: string
        score:
          type: number
        grade:
          type: string
        issues:
          type: array
          items:
            type: string
      required:
      - indicator
      - score
      - grade
      - issues
      description: 类型已定义，当前端点始终返回空数组。
      example:
        indicator: 玉米现货价格
        score: 90
        grade: B
        issues: []
    QualityDistribution:
      type: object
      properties:
        grade_a:
          type: integer
          minimum: 0
        grade_b:
          type: integer
          minimum: 0
        grade_c:
          type: integer
          minimum: 0
        grade_d:
          type: integer
          minimum: 0
        grade_m:
          type: integer
          minimum: 0
      required:
      - grade_a
      - grade_b
      - grade_c
      - grade_d
      - grade_m
      description: 当前全零占位，不查询实际质量。
      example: *id033
    Notification:
      type: object
      properties:
        id:
          type: string
        level:
          type: string
          enum:
          - info
          - success
          - warning
          - error
        title:
          type: string
        message:
          type: string
        timestamp: *id024
        metadata: *id034
      required:
      - id
      - level
      - title
      - message
      - timestamp
      example: *id035
    ScheduledJob:
      type: object
      properties:
        id: *id009
        name:
          type: string
        collector_id:
          type: string
        cron_expression:
          type: string
          description: UTC 六字段，包含秒。
        enabled:
          type: boolean
        description:
          type: string
          nullable: true
        status:
          type: string
          enum:
          - idle
          - running
          - success
          - failed
        last_run:
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
        last_error:
          type: string
          nullable: true
        total_runs:
          type: integer
          format: int64
        success_count:
          type: integer
          format: int64
        failed_count:
          type: integer
          format: int64
        created_at: *id024
        next_run:
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
        timezone:
          type: string
          enum:
          - UTC
      required:
      - id
      - name
      - collector_id
      - cron_expression
      - enabled
      - description
      - status
      - last_run
      - last_error
      - total_runs
      - success_count
      - failed_count
      - created_at
      - next_run
      - timezone
      description: 实际序列化字段为 cron_expression，不是旧模型中的 cron_expr。
      example: *id036
    JobExecution:
      type: object
      properties:
        id: *id009
        job_id: *id009
        trigger_type:
          type: string
          enum:
          - scheduled
          - manual
        status:
          type: string
          enum:
          - running
          - success
          - failed
        started_at: *id024
        completed_at:
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
        records_collected:
          type: integer
        collection_run_id:
          type: string
          nullable: true
        error_message:
          type: string
          nullable: true
      required:
      - id
      - job_id
      - trigger_type
      - status
      - started_at
      - completed_at
      - records_collected
      - collection_run_id
      - error_message
      example: *id037
    AsyncJob:
      type: object
      properties:
        id: *id009
        collector_name:
          type: string
        adapter_id:
          type: string
        run_id:
          type: string
          nullable: true
        max_items:
          type: integer
        status:
          type: string
          enum:
          - queued
          - running
          - succeeded
          - failed
        progress:
          type: integer
          minimum: 0
          maximum: 100
        phase:
          type: string
          description: queued/starting/scanning/collected/persisting/succeeded/failed 等阶段；非耗时百分比。
        details:
          type: object
          additionalProperties: true
        result:
          type: object
          nullable: true
          additionalProperties: true
        error_message:
          type: string
          nullable: true
        created_at: *id024
        started_at:
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
        completed_at:
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
        updated_at: *id024
      required:
      - id
      - collector_name
      - adapter_id
      - run_id
      - max_items
      - status
      - progress
      - phase
      - details
      - result
      - error_message
      - created_at
      - started_at
      - completed_at
      - updated_at
      example: *id038
    RawRecord:
      type: object
      properties:
        id: *id009
        collector_id:
          type: string
        business_date: *id030
        indicator_name:
          type: string
        value: &id040
          type: string
          description: 数据库 Decimal 以十进制字符串序列化，不能按 JSON number 处理。
          pattern: ^-?\d+(\.\d+)?$
        unit:
          type: string
        region:
          type: string
          nullable: true
        source_url:
          type: string
        original_text:
          type: string
          nullable: true
        dedup_key:
          type: string
        collected_at: *id024
        created_at:
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
        updated_at:
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
      required:
      - id
      - collector_id
      - business_date
      - indicator_name
      - value
      - unit
      - region
      - source_url
      - original_text
      - dedup_key
      - collected_at
      - created_at
      - updated_at
      example: *id039
    StandardRecord:
      type: object
      properties:
        id: *id009
        business_date: *id030
        indicator_name:
          type: string
        value: *id040
        unit:
          type: string
        region:
          type: string
          nullable: true
        quality_grade:
          type: string
        quality_score:
          type: string
          description: 数据库 Decimal 以十进制字符串序列化，不能按 JSON number 处理。
          pattern: ^-?\d+(\.\d+)?$
          nullable: true
        quality_issues: *id034
        source_id:
          type: string
        raw_record_id:
          type: string
          description: UUID。
          format: uuid
          nullable: true
        collected_at: *id024
        standardized_at: *id024
        version:
          type: integer
        is_latest:
          type: boolean
        metadata: *id034
        created_at:
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
        updated_at:
          type: string
          description: RFC 3339 时间，包含时区。
          format: date-time
          nullable: true
      required:
      - id
      - business_date
      - indicator_name
      - value
      - unit
      - region
      - quality_grade
      - quality_score
      - quality_issues
      - source_id
      - raw_record_id
      - collected_at
      - standardized_at
      - version
      - is_latest
      - metadata
      - created_at
      - updated_at
      example: *id041
    Lineage:
      type: object
      properties:
        standard_record:
          $ref: '#/components/schemas/StandardRecord'
        raw_record:
          type: object
          properties:
            id:
              type: string
              description: UUID。
              format: uuid
            collector_id:
              type: string
            business_date:
              type: string
              description: 业务日期，ISO 8601。
              format: date
            indicator_name:
              type: string
            value:
              type: string
              description: 数据库 Decimal 以十进制字符串序列化，不能按 JSON number 处理。
              pattern: ^-?\d+(\.\d+)?$
            unit:
              type: string
            region:
              type: string
              nullable: true
            source_url:
              type: string
            original_text:
              type: string
              nullable: true
            dedup_key:
              type: string
            collected_at:
              type: string
              description: RFC 3339 时间，包含时区。
              format: date-time
            created_at:
              type: string
              description: RFC 3339 时间，包含时区。
              format: date-time
              nullable: true
            updated_at:
              type: string
              description: RFC 3339 时间，包含时区。
              format: date-time
              nullable: true
          required:
          - id
          - collector_id
          - business_date
          - indicator_name
          - value
          - unit
          - region
          - source_url
          - original_text
          - dedup_key
          - collected_at
          - created_at
          - updated_at
          example:
            id: f55ce408-550f-400a-8a03-94839115ac6a
            collector_id: sina_production
            business_date: '2026-10-22'
            indicator_name: 玉米现货价格
            value: '2040.0000'
            unit: 元/吨
            region: 山东
            source_url: https://finance.sina.com.cn/money/future/C/
            original_text: null
            dedup_key: example-key
            collected_at: '2026-10-22T01:00:00Z'
            created_at: '2026-10-22T01:00:00Z'
            updated_at: '2026-10-22T01:00:00Z'
          nullable: true
        lineage_chain:
          type: array
          items:
            type: string
      required:
      - standard_record
      - raw_record
      - lineage_chain
      example: *id042
    CollectorResult:
      type: object
      properties:
        collector_id:
          type: string
        records_collected:
          type: integer
          minimum: 0
        run_id:
          type: string
      required:
      - collector_id
      - records_collected
      - run_id
      example: *id007
    AdapterRunAccepted:
      type: object
      properties:
        run_id:
          type: string
        status:
          type: string
          enum:
          - running
        message:
          type: string
      required:
      - run_id
      - status
      - message
      example: *id043
    AsyncJobAccepted:
      type: object
      properties:
        job_id: *id009
        status:
          type: string
          enum:
          - queued
        status_url:
          type: string
      required:
      - job_id
      - status
      - status_url
      example: *id044
    ScheduleCreated:
      type: object
      properties:
        job_id: *id009
      required:
      - job_id
      example: *id045
    ScheduleTriggered:
      type: object
      properties:
        execution_id: *id009
        status:
          type: string
          enum:
          - running
      required:
      - execution_id
      - status
      example: *id046
    StandardizationResult:
      type: object
      properties:
        success_count:
          type: integer
          minimum: 0
        error_count:
          type: integer
          minimum: 0
      required:
      - success_count
      - error_count
      example: *id047
    PromotionResult:
      type: object
      properties:
        promoted_count:
          type: integer
          minimum: 0
      required:
      - promoted_count
      example: *id048
    CornError:
      type: object
      properties:
        success:
          type: boolean
          enum:
          - false
        error:
          type: string
      required:
      - success
      - error
      example:
        success: false
        error: limit must be between 1 and 100
    ApplicationFailure:
      type: object
      properties:
        success:
          type: boolean
          enum:
          - false
        data:
          nullable: true
          description: 此错误格式的 data 恒为 null。
          enum:
          - null
        message:
          type: string
      required:
      - success
      - data
      - message
      example:
        success: false
        data: null
        message: Record not found
    CreateSource:
      type: object
      properties:
        id:
          type: string
        name:
          type: string
        domain:
          type: string
          nullable: true
        description:
          type: string
          nullable: true
      required:
      - id
      - name
      example: *id049
    UpdateSource:
      type: object
      properties:
        name:
          type: string
          nullable: true
        domain:
          type: string
          nullable: true
        description:
          type: string
          nullable: true
        status:
          type: string
          nullable: true
      description: 所有字段可选；null 与缺省都表示不修改，不能用 null 清空字段。
      example: *id050
    CreateAdapter:
      type: object
      properties:
        id:
          type: string
        name:
          type: string
        script_file:
          type: string
        source_id:
          type: string
        topic_name:
          type: string
      required:
      - id
      - name
      - script_file
      - source_id
      - topic_name
      example: *id051
    UpdateAdapter:
      type: object
      properties:
        name:
          type: string
          nullable: true
        script_file:
          type: string
          nullable: true
        topic_name:
          type: string
          nullable: true
      description: 不能通过该接口更改 source_id 或 status；null 不更新字段。
      example: *id052
    RunCollector:
      type: object
      properties:
        collector_name:
          type: string
          description: 采集器名称；也接受别名字段 collector_id。不可同时传两字段，不可为空白。
        collector_id:
          type: string
          description: collector_name 的兼容别名，与其二选一。
        max_items:
          type: integer
          description: 可选；null 使用默认值。
          minimum: 1
          maximum: 4294967295
          default: 100
          nullable: true
      description: 必须提供 collector_name 或 collector_id 中的一个；两者同传被 serde 视为重复字段并返回 422。
      example: *id053
      oneOf:
      - required:
        - collector_name
        not:
          required:
          - collector_id
      - required:
        - collector_id
        not:
          required:
          - collector_name
    SubmitAsyncJob:
      type: object
      properties:
        collector_name:
          type: string
          description: 采集器名称；也接受别名字段 collector_id。不可同时传两字段，不可为空白。
        collector_id:
          type: string
          description: collector_name 的兼容别名，与其二选一。
        max_items:
          type: integer
          description: 可选；null 使用默认值。
          minimum: 1
          maximum: 1000
          default: 100
          nullable: true
      description: 必须提供 collector_name 或 collector_id 中的一个；两者同传被 serde 视为重复字段并返回 422。
      example: *id054
      oneOf:
      - required:
        - collector_name
        not:
          required:
          - collector_id
      - required:
        - collector_id
        not:
          required:
          - collector_name
    Standardize:
      type: object
      properties:
        raw_record_ids:
          type: array
          items:
            type: string
            description: 原始记录 UUID；无法解析的项计入 error_count。
      required:
      - raw_record_ids
      example: *id055
    MarkRead:
      type: object
      properties:
        notification_id:
          type: string
      required:
      - notification_id
      example: *id056
    CreateSchedule:
      type: object
      properties:
        name:
          type: string
          description: 不可为空白。
        collector_id:
          type: string
          description: 必须唯一解析到数据库适配器。
        cron_expression:
          type: string
          description: UTC，秒 分 时 日 月 周。
        description:
          type: string
          nullable: true
        enabled:
          type: boolean
          default: true
          nullable: true
      required:
      - name
      - collector_id
      - cron_expression
      example: *id057
    ToggleSchedule:
      type: object
      properties:
        enabled:
          type: boolean
      required:
      - enabled
      example: *id058
x-source-baseline:
  date: '2026-10-22'
  git_head: 82d38ce914624174b956b51a53c24edb323e8e32
  dirty_worktree: true
  files:
    backend-rust/src/main.rs: 0b8dcb207080f9e08f9549516529249c9cdab0db889ff9b18e0c61138c660e3b
    backend-rust/src/handlers.rs: 16ae06189fe801f4f5429871e76343232677ff258e1ca3d7c350d565a1b8c932
    backend-rust/src/collection_handlers.rs: fca9b27e8d001d03f60d860bceaca75733c4c948b4734a843510895b36caca1b
    backend-rust/src/async_jobs.rs: 2e0bbb79646be893f5fb4c11c371f829c78ebd689381a34402285e0f8f9bef54
    backend-rust/src/lineage_handlers.rs: a37ea70363213a735bc65d59f23458a8b4165822f5cfc9252a10a182c888a671
    backend-rust/src/models.rs: aebd6cd83767bfdd4475290b4ae2f712b24c895afd816fd2b18870d1c90892d2
    backend-rust/src/errors.rs: c780c2c19d0278fa4fd0f9cb01df1ec2a182cb15894f6552f7986e7696b9ac80
    backend-rust/src/standardization.rs: 0067be6c83b2f54b22d1509d183995b376ab2a7c58106c277b92503e35a29dd9
    backend-rust/src/db/collection_entities.rs: 0f59061c81183536486d8311c04da8a1dde8f1d5f61776daf423b47f759f084d
    backend-rust/src/db/entities.rs: 947dd4c5f301b918f5a4a2f612bd6ac155a8ce0a7f01bc11487acc21a35bb363
    backend-rust/src/scheduler/job_manager.rs: 454b66503b2a64d0a8061309d553f80219ec334487fc24dce49deb5d7b91724e
    backend-rust/src/notification/service.rs: 7763b0d3462a770b899399cf59cdd4e08bb6654c249a7b46433e38ee2ad4fe29
  note: 已有本地接口契约快照；本次仅生成 Markdown，不运行验证器或接口测试。代码快照不代表已部署镜像或生产验收结果。
```
