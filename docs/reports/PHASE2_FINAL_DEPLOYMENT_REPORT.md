# Phase 2 最终部署复验报告

复验时间：2026-10-22，Asia/Shanghai。

## 结论

**backend 重建和 Job 列表验证成功，Boyar 真实采集成功；DCE 上游返回 412，完整生产发布门禁仍未通过。**

用户要求五项问题修复并复验后发布。QA 交付报告只将三项标记为已修复，
另外两项改列为缺失功能；此范围变更尚未获用户确认。
本次快速复验不支持使用 `All E2E tests passing` 或 `Production ready` 声明。
另一位工程师已创建并推送 `2e0613a`；其提交说明包含这些声明，
但 DCE 的真实任务失败，不支持“全部通过”的结论。本报告以实际任务结果纠正说明，
不改写已经发布的提交历史，也不移动 `v2.0.0-phase2` 标签。

## 五项问题状态

| 问题 | 本次核查 | 发布状态 |
| --- | --- | --- |
| Boyar 并发锁 | 真实任务成功，取得 1 条；重叠异步提交返回 409；真实 Redis 竞争单测通过。释放异常模拟仍显示只能等租约过期或安全恢复 | 正常链路通过；异常恢复未闭环 |
| 异步 Job 系统 | 重建后 `/api/jobs` HTTP 200，返回 9 项；单任务查询、入队和终态记录已验证 | 本轮通过 |
| DCE 配置 | 数据库确认唯一 `adapter_dce_futures`；任务已入队并启动，但官方来源返回 HTTP 412，终态 failed | 配置验证通过；真实采集失败 |
| Feedtrade 注册 | `run_collector.py` 中无 `feedtrade` 注册，QA 标记未实现 | 未完成 |
| 100ppi 注册 | `run_collector.py` 中无 `100ppi` 注册，QA 标记未实现 | 未完成 |

Boyar 释放异常诊断仅使用 FakeRedis 和模拟扫描，不访问真实站点或删除实际锁。
模拟令 `lock.release()` 抛出连接异常，首次调用返回后锁仍在，第二次调用抛出
`Another Boyar incremental collection is running`。
这说明当前补丁提供异常保护，但不能作为残留锁恢复已修复的证据。
真实 Redis 锁已有 TTL；不得在未核实持锁运行状态时直接删除锁。

## 快速验证结果

| 验证 | 结果 | 边界 |
| --- | --- | --- |
| Python 采集器单测 | 新镜像中 103/103 通过，无跳过 | 已启用使用唯一测试键的真实 Redis 测试；站点 HTTP 使用模拟数据 |
| 前端 API 单测 | 5/5 通过 | 非浏览器 E2E |
| 前端 TypeScript 检查 | 通过 | 本轮修复两处 Tooltip 日期参数类型错误后复跑；未执行生产构建 |
| Rust backend 检查 | `cargo check --tests` 和 Docker release 构建通过，有编译警告 | 构建不等于执行完整 Rust 测试 |
| 运维脚本单测 | 11/11 通过 | 使用测试替身，不是生产备份恢复演练 |
| corn_rs 集成测试 | 9/9 通过 | 使用已有 `.venv/corn-rs` 扩展；本轮未从最新源码重建扩展 |
| 运行服务健康检查 | 重建后容器 healthy，`/health` HTTP 200 | 复验时状态，不等于长期可用性承诺 |
| 运行服务 Job 列表 | 重建后 `/api/jobs` HTTP 200 | 返回 success=true 和任务数组 |
| 真实 Boyar 任务 | succeeded，records_collected=1 | 限制 max_items=1；重叠提交返回 409 |
| 真实 DCE 任务 | failed，HTTP 412 | 未获取并持久化真实行情，不能算 E2E 成功 |
| 补丁空白检查 | `git diff --check` 通过 | 不代替安全审计或功能验证 |

复验命令：

```bash
uv run --with redis --with requests --with beautifulsoup4 --with lxml --with tenacity \
  python -m unittest discover -s collectors-python/tests -v
(cd frontend && npm test)
(cd frontend && ./node_modules/.bin/tsc --noEmit --incremental false)
cargo check --locked --offline --manifest-path backend-rust/Cargo.toml --tests
python3 -m unittest discover -s tests/ops -v
.venv/corn-rs/bin/python tests/test_integration.py
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:18000/health
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:18000/api/jobs
git diff --check
```

本机测试日志：`/tmp/corn-phase2-python-final.log`、`/tmp/corn-phase2-rust-final.log`。
新镜像内启用集成测试的命令为：

```bash
docker exec -i corn_backend python3 - <<'PY'
import os, sys, unittest
sys.path.insert(0, '/app/collectors-python')
os.environ['BOYAR_TEST_REDIS_URL'] = os.environ['REDIS_URL']
os.environ['CURSOR_TEST_REDIS_URL'] = os.environ['REDIS_URL']
suite = unittest.defaultTestLoader.discover('/app/collectors-python/tests')
result = unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(not result.wasSuccessful())
PY
```

真实任务证据（UTC）：

- Boyar：`5acc567d-b8f8-4759-bcfe-632439b88aeb`，2026-10-22 08:35:02 完成，
  `succeeded`，`records_collected=1`，错误为空。
- DCE：`720926b3-4221-4e50-b597-a64b398a7807`，2026-10-22 08:31:27 完成，
  `failed`，`HTTPError: HTTP Error 412: Precondition Failed`。
- 镜像：`sha256:2a8b8c26cc792d283026cfd9cab68a878fa720eb6a679cc380a150756544f982`。
- 后续尝试检查终态后的 Redis 锁时，Docker socket 已不可用；因此不宣称已额外确认
  此次真实运行结束后的锁删除状态。此前真实 Redis 释放/竞争单测已通过。

旧报告中的“代码审查确认”不视为真实并发或 API 调用通过记录；
`PHASE2_E2E_TEST_RESULTS.md` 中原有五项失败，尚无五项全部通过的新 E2E 证据。

## 部署和运维交付

- 部署入口、环境变量及故障排查：`docs/DEPLOYMENT.md`。
- 日志、监控配置与限制：`docs/MONITORING.md`。
- 备份策略：`docs/BACKUP_STRATEGY.md`。
- 隔离恢复流程：`docs/RESTORE_GUIDE.md`。
- 上述脚本的快速测试通过，但本轮未执行生产部署、真实恢复演练或告警通知验收。
- 应用鉴权与公网暴露限制按部署指南执行，不能把本报告视作安全上线批准。

## 容器连接配置修复

初次重建后发现开发 `.env` 中的 `DATABASE_URL`、`REDIS_URL` 为主机访问地址，
容器内部使用 `localhost:15432/16380` 导致启动失败。
`docker-compose.yml` 已改用专用 `BACKEND_DATABASE_URL`、`BACKEND_REDIS_URL` 覆盖，
默认使用服务 DNS `postgres:5432`、`redis:6379`。
现有凭据和服务实际认证方式写入被忽略的本地 `.env`，权限 0600，
保留主机用连接变量；没有重建数据库或 Redis，也没有修改数据卷。

本次现存 Redis 未启用 requirepass，临时保持其实际配置以避免干扰其他运行。
这不是生产安全批准；生产认证配置应按 `docs/DEPLOYMENT.md` 在维护窗口协调实施。

## Git 与发布状态

只读核对确认 GitHub `main` 与本地均已包含
`2e0613a507cd19ba656f593e1b2ec5aade264b1a`，无需重复提交这批代码。
该提交由并发工程师创建并已推送，包含 42 个文件。
后续修正提交只更新实际验证结论、补充配置说明并移除本地运行文件的 Git 跟踪；
保留磁盘文件，不 amend、不强推，不删除远程历史。
`.ccb/` 为本次误跟踪，`team_config.json`、`opencode.jsonc` 在更早历史已被跟踪，
仅添加 ignore 不能取消跟踪；本次一并取消跟踪，落实用户不提交这些本地配置的要求。
生产密钥、`.env` 和本地运行数据均不得加入修正提交。
本地 `v2.0.0-phase2` 指向 `82d38ce914624174b956b51a53c24edb323e8e32`。
只读 `git ls-remote` 核对远程标签仍指向该提交；因发布门禁未通过，不更新标签。

补充修正前的最近三条提交：

```text
2e0613a fix(phase2): E2E bug fixes and Docker rebuild
3193d19 docs: Add API specification (OpenAPI 3.0.3)
82d38ce feat(phase2): Complete Phase 2 - Advanced Data Collection System
```

## 发布前必须完成

1. 修复并提供 Boyar 锁竞争、失败释放及安全恢复的可重复验证证据。
2. 在固定构建上补充完整 E2E；Job 列表和本轮真实异步链路已有证据，不再列为旧镜像 404。
3. 解决 DCE 官方接口 412 后验证真实数据持久化；不得用 Mock 或仅入队成功替代真实采集成功。
4. 完成 Feedtrade、100ppi 实现与注册，或由用户明确批准延期并调整发布范围。
5. 在冻结的代码版本上重跑关键 E2E、审查暂存内容及敏感信息，再创建与实际结果一致的提交并推送。
