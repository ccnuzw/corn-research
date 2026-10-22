# Collectors Python - 数据采集器

**语言**: Python 3.11+  
**原则**: 一站一器，灵活快速

## 目录结构

```
collectors/
├── base.py              # 采集器基类
├── boyar.py            # 博亚和讯
├── sina.py             # 新浪财经
├── dce.py              # 大商所
├── netease.py          # 网易订阅
└── __init__.py
```

## 快速开始

```bash
pip install -r requirements.txt
python -m collectors.boyar
```

## 博亚生产采集器

```bash
export REDIS_URL=redis://localhost:16380/0
python run_collector.py --collector boyar_production --max-items 10
```

配置位于 `config.py`：
- `REDIS_URL`：默认 `redis://localhost:16380/0`；Docker Compose 已提供 `redis://redis:6379/0`。
- `BOYAR_START_ARTICLE_ID`：无游标时首次起点，默认 `1267743`，可按回填范围调整。
- `BOYAR_SCAN_LIMIT`：单次最多扫描文章数，默认 150；`max_items` 限制返回的有效记录数。
- Redis key：`collector:boyar:last_article_id`；保留原有键值，不需要清空或迁移。

增量规则：首次从配置起点开始，之后从 Redis 的 `last_id + 1` 开始。
成功处理的非目标文章也推进游标；显式起点不大于游标时按重复处理并停止。
遇到 404/410 停止，缺页不推进游标；因此文章 ID 存在永久空洞时需要人工确认后调整起点。
Redis 不可用、游标损坏、存档失败或网络重试耗尽时抛错，不静默重扫。
整批抓取解析和 HTML 存档成功后提出游标更新；通过后端执行时，全部记录入库成功后才确认写入 Redis。
Redis 锁防止同时扫描；入库确认期间的重复扫描由数据库去重和单调游标更新处理。
`incremental=False` 可用于诊断或历史回填，不读取/修改生产游标。

每次请求（包括重试）随机等待 1–3 秒限速，User-Agent 轮换并添加 Referer。
首次请求后最多重试 3 次，指数退避 1、2、4 秒；限速可能进一步延长重试间隔。
仅重试网络异常、408、429 和 5xx；403 等永久错误直接失败。
日志同时写入 stderr 和 `/app/logs/collectors/boyar.log`，stdout 仅输出运行器 JSON。
日志按 10MB 轮转，保留 5 份备份；跨进程文件锁保护轮转，重复初始化不会添加重复 handler。
可通过 `COLLECTOR_LOG_DIR` 调整目录，本地开发应设为可写目录，例如 `./logs/collectors`。

所有成功返回的文章 HTML（包括非目标文章）按 UTF-8 明文原子写入：
`/app/data/html/boyar/YYYY-MM-DD/article_ID.html`，有效数据的 `metadata.html_path` 返回该路径。
已有的 `data/raw/html/boyar/` gzip 历史存档保留不动；新存档不再写该旧目录。
HTML 文件内容先 flush/fsync，再原子替换；写入失败不推进游标。
日志记录开始、扫描范围、HTML 路径、重试原因、失败堆栈，以及 `run_finished` JSON 统计：
状态、扫描数、请求数、重试数、存档数、有效记录数、耗时，以及增量游标前后值。

Compose 挂载 `./data:/app/data`、`./logs:/app/logs`，重建容器不会删除宿主机存档。
检查示例：
```bash
ls data/html/boyar/$(date +%F)/
tail -n 20 logs/collectors/boyar.log
docker compose up -d --build --wait backend
```

验证命令（在项目根目录执行）：
```bash
python3 -m unittest discover -s collectors-python/tests -v
BOYAR_TEST_REDIS_URL=redis://localhost:16380/0 \
  python3 -m unittest discover -s collectors-python/tests -v
docker exec corn_redis redis-cli GET collector:boyar:last_article_id
```

对真实站点做两次有界增量验证（会推进生产游标）：
```bash
docker exec corn_backend python3 /app/collectors-python/tests/verify_boyar_live.py --scan-limit 2
```

真实 Redis 测试使用随机 `test:collector:boyar:*` key，并自动清理；HTTP 为模拟响应，
不表示真实站点已通过。生产 key 只应由真实采集推进，不要用测试 ID 初始化。

## 统一游标管理（Phase 2 Day 1 Task 2）

`cursor.py` 提供 `CursorManager(namespace, kind='int')`，支持正整数文章 ID 和严格
`YYYY-MM-DD` 日期。`BaseCollector.configure_cursor/get_cursor/advance_cursor` 供采集器复用；
未配置游标的采集器保持原行为。Redis 异常或损坏值直接报错，不把异常当作首次采集。
CAS 原子更新防止并发回退，也避免 Lua 浮点整数精度问题。

新浪按每日首份快照增量采集，现货、期货独立推进：
- `collector:sina:last_date`：现货报告的业务日期。
- `collector:sina:last_date:futures`：期货报价的业务日期，默认符号 `nf_C0`。
- 同日第二次采集返回 0 条；不是盘中报价订阅，也不修改已保存的当日首份快照。
- `max_items` 截断某日期的数据时，不推进该流的日期游标；重试应使用足够大的批量（默认 100）。
- 不使用网页发布日期或采集当天日期冒充业务日期；已知旧报告跳过抓取。
- `SINA_CURSOR_KEY` 仅用于隔离环境或明确的运维覆盖；常规部署无需设置。
- `SINA_FUTURES_SYMBOLS` 应保持稳定；当天新增符号需单独回填，不能依赖已推进的流游标。

后端执行链路为：`run_collector.py` 暂存更新 → 输出 `cursor_updates` → Rust 校验/入库所有
返回记录 → `commit_cursors.py` 确认 Redis 游标。任意入库失败均不确认；Redis 确认失败则
本次任务标为失败，人工重试会去重已写入的数据。异步、适配器和调度任务走相同确认链路。
旧博亚同步计数接口不入库，因此也不推进游标；生产采集请使用异步或适配器接口。

直接调用采集器类的 `.collect()` 仍会自行提交游标；命令行运行器只输出更新提案，
不会把未入库的数据标为已完成。不要在尚未持久化输出时手动执行确认脚本。
`incremental=False` 为不读写游标的诊断模式，需直接调用采集器类。

SQL 与 Redis 并非一个事务：入库后、确认前崩溃可能重复抓取，但不提前越过未入库数据。
当前仍为单后端恢复模型，不提供恰好一次投递、自动重放或完整历史回填保证。
真实链路测试与生产键值见 `docs/reports/PHASE2_DAY1_TASK2.md`（项目根目录）。
