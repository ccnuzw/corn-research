# Phase 2 最终部署复验报告

复验时间：2026-10-22，Asia/Shanghai。

## 结论

**发布门禁未通过，暂不提交最终发布 commit、不推送、不移动发布标签。**

用户要求五项问题修复并复验后发布。QA 交付报告只将三项标记为已修复，
另外两项改列为缺失功能；此范围变更尚未获用户确认。
本次快速复验不支持使用 `All E2E tests passing` 或 `Production ready` 声明。

## 五项问题状态

| 问题 | 本次核查 | 发布状态 |
| --- | --- | --- |
| Boyar 并发锁 | 新增释放异常捕获；故障模拟确认释放失败后下一次采集仍被锁阻止，直到租约过期或安全恢复 | 未闭环 |
| 异步 Job 系统 | 源码已注册 `GET /api/jobs`，Rust 编译检查通过；当前运行服务该接口返回 404 | 待修复版本部署后复验 |
| DCE 配置 | QA 报告称已向当前数据库插入配置；仓库已有 `010_dce_corn_prices.sql`，本次未独立复验数据库及真实采集链路 | 待集成复验 |
| Feedtrade 注册 | `run_collector.py` 中无 `feedtrade` 注册，QA 标记未实现 | 未完成 |
| 100ppi 注册 | `run_collector.py` 中无 `100ppi` 注册，QA 标记未实现 | 未完成 |

Boyar 诊断仅使用 FakeRedis 和模拟扫描，不访问真实站点或删除实际锁。
模拟令 `lock.release()` 抛出连接异常，首次调用返回后锁仍在，第二次调用抛出
`Another Boyar incremental collection is running`。
这说明当前补丁提供异常保护，但不能作为残留锁恢复已修复的证据。
真实 Redis 锁已有 TTL；不得在未核实持锁运行状态时直接删除锁。

## 快速验证结果

| 验证 | 结果 | 边界 |
| --- | --- | --- |
| Python 采集器单测 | 103 项，97 通过、6 跳过 | 未设置真实 Redis 测试 URL；不等于真实采集 E2E |
| 前端 API 单测 | 5/5 通过 | 非浏览器 E2E |
| 前端 TypeScript 检查 | 通过 | 本轮修复两处 Tooltip 日期参数类型错误后复跑；未执行生产构建 |
| Rust backend 检查 | `cargo check --tests` 通过，有编译警告 | 检查不执行测试；本轮未重试原先受主机链接器影响的 Rust 测试 |
| 运维脚本单测 | 11/11 通过 | 使用测试替身，不是生产备份恢复演练 |
| corn_rs 集成测试 | 9/9 通过 | 使用已有 `.venv/corn-rs` 扩展；本轮未从最新源码重建扩展 |
| 运行服务健康检查 | `/health` HTTP 200 | 只证明当前服务可达 |
| 运行服务 Job 列表 | `/api/jobs` HTTP 404 | 当前运行实例未验证新增接口成功 |
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
旧报告中的“代码审查确认”不视为真实并发或 API 调用通过记录；
`PHASE2_E2E_TEST_RESULTS.md` 中原有五项失败，尚无五项全部通过的新 E2E 证据。

## 部署和运维交付

- 部署入口、环境变量及故障排查：`docs/DEPLOYMENT.md`。
- 日志、监控配置与限制：`docs/MONITORING.md`。
- 备份策略：`docs/BACKUP_STRATEGY.md`。
- 隔离恢复流程：`docs/RESTORE_GUIDE.md`。
- 上述脚本的快速测试通过，但本轮未执行生产部署、真实恢复演练或告警通知验收。
- 应用鉴权与公网暴露限制按部署指南执行，不能把本报告视作安全上线批准。

## Git 与发布状态

本轮未执行 `git add`、`git commit`、`git push` 或标签修改，保留工作树供 QA 继续修复。
不得将 `.ccb/`、`team_config.json`、`opencode.jsonc`、生产密钥和本地运行数据纳入后续提交。
本轮只读基线：`3193d19e25ba96dacc7ac21d1bc559f6a5df3f9e`。
本地 `v2.0.0-phase2` 指向 `82d38ce914624174b956b51a53c24edb323e8e32`。
只读 `git ls-remote` 核对：GitHub `main` 仍为上述 `3193d19`，远程 Phase 2 标签
仍指向上述 `82d38ce`，与本地基线一致；本轮没有产生新的远程发布。

当前最近三条提交，不是本轮新增提交：

```text
3193d19 docs: Add API specification (OpenAPI 3.0.3)
82d38ce feat(phase2): Complete Phase 2 - Advanced Data Collection System
7973318 feat(phase1): Complete Phase 1 - Data Collection System
```

## 发布前必须完成

1. 修复并提供 Boyar 锁竞争、失败释放及安全恢复的可重复验证证据。
2. 部署包含新路由的构建，验证 Job 列表、状态查询和异步执行链路。
3. 在隔离环境验证 DCE 迁移、唯一 adapter 解析及真实数据持久化。
4. 完成 Feedtrade、100ppi 实现与注册，或由用户明确批准延期并调整发布范围。
5. 在冻结的代码版本上重跑关键 E2E、审查暂存内容及敏感信息，再创建与实际结果一致的提交并推送。
