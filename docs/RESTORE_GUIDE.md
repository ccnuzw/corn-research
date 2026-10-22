# Phase 2 备份恢复操作流程

生产入口见 [DEPLOYMENT.md](DEPLOYMENT.md)，备份目标和留存见
[BACKUP_STRATEGY.md](BACKUP_STRATEGY.md)。本流程用于**隔离恢复**，不直接覆盖生产。
恢复记录至少包含批准人、快照 ID、代码版本、镜像版本、开始/结束时间和一致性核验结果。

## 1. 恢复前置检查

1. 冻结生产写入或明确只是离线演练，宣布允许的数据损失范围。
2. 从受控异地存储下载并解密到权限0700目录，不将密码或数据上传 Git。
3. 使用备份对应提交、兼容 PostgreSQL 主版本及扩展镜像；不能将 TimescaleDB dump
   在缺扩展的普通 PostgreSQL 直接当作可恢复。当前 restore Compose 只适用于普通 PG16。
4. 运行 `python3 scripts/verify-backup.py "$BACKUP"`，所有校验通过；失败即停止。
5. 在独立主机/目录准备恢复环境。不要对生产目录运行以下操作。

```bash
# 在隔离副本仓库根目录执行；BACKUP 必须是可信快照目录的绝对路径。
: "${BACKUP:?Set the absolute path to a verified backup}"
python3 scripts/verify-backup.py "$BACKUP"
cp .env.production.example .env.restore
chmod 600 .env.restore
# 编辑：COMPOSE_PROJECT_NAME=corn-restore-YYYYMMDDHHMM，且绝不能使用生产项目名。
# 两个密码分别用 openssl rand -hex 32 重新生成，不复用生产密码。
restore_dc() { docker compose --env-file .env.restore -f docker-compose.restore.yml "$@"; }
restore_dc config --quiet
restore_dc ps -a
```

使用专用 `docker-compose.restore.yml`，只含 postgres、redis，使用 `restore_*` 数据卷，
没有生产 migrations 初始化挂载、后端、调度器、网关和公开端口。不要与生产 Compose 叠加。
即使项目名误设为生产，restore 卷名也与生产不同，但仍须核对并使用全新项目名。
本流程不包含 `down -v` / `volume rm`；卷已存在时换全新恢复项目，不清理在用卷。

## 2. 恢复 PostgreSQL

先只启动 PostgreSQL，**此时不要启动 Redis**。

```bash
restore_dc up -d --wait postgres
# 确认业务表尚不存在，查询应返回0；非0时停止，改用新项目/卷。
restore_dc exec -T postgres sh -ec \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -At -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = '\''public'\'';"'
restore_dc exec -T postgres sh -ec \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl --single-transaction --exit-on-error' \
  < "$BACKUP/postgres.dump"
```

`--single-transaction` 使失败不留下半次导入；恢复前必须是空业务数据库。
不得使用 `--clean` 对生产数据库“试一下”。恢复失败先保留错误日志并脱敏，修复兼容性后
使用新恢复项目重试，而非反复导入一个未知状态数据库。

## 3. 恢复 Redis（先导入 RDB，再第一次启动）

Redis AOF 优先于 dump.rdb，不能把 RDB 复制到已有 AOF 的卷期待它自动生效。
使用一次性容器向新卷写入数据；该命令只执行 shell，不启动 Redis 服务。

```bash
restore_dc run --rm -T --no-deps --user root --entrypoint sh redis -ec '
  test -z "$(find /data -mindepth 1 -maxdepth 1 -print -quit)"
  cat > /data/dump.rdb
  redis-check-rdb /data/dump.rdb
  chown redis:redis /data/dump.rdb
' < "$BACKUP/redis.rdb"
restore_dc up -d --wait redis
restore_dc exec -T redis redis-cli ping
```

目录非空或检查失败立即停止，不删除旧 AOF，不使用 FLUSHALL。
新密码由 `.env.restore` 的 REDISCLI_AUTH 应用，密码不会包含在 RDB 快照中。

## 4. 恢复 HTML 与核验数据

仅对受信任、校验通过的归档操作。先审查列表：路径必须在 `data/` 下，无绝对路径、`..`
穿越及指向目录外的符号链接；在非 root 账号下解包到独立空目录，避免覆盖仓库文件。

```bash
tar -tzf "$BACKUP/html-data.tar.gz"
mkdir -p restore-files
tar -xzf "$BACKUP/html-data.tar.gz" -C restore-files
restore_dc exec -T postgres sh -ec \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' <<'SQL'
SELECT count(*), max(business_date) FROM raw_collection_records;
SELECT count(*), max(business_date) FROM collection_records;
SELECT status, count(*) FROM collection_runs GROUP BY status;
SELECT status, count(*) FROM async_jobs GROUP BY status;
SELECT id, enabled, collector_id FROM scheduled_jobs;
SQL
restore_dc exec -T redis redis-cli --scan --pattern 'collector:*'
```

与备份时的业务基线比对记录数、最新日期、关键游标和 HTML 文件数/抽样内容。
校验 manifest 不能代替业务核验。检查唯一索引、历史查询和去重契约。
若出现锁，先确认原持有者已不存在并等待 TTL，不能盲目删锁或把游标重置为今天。

## 5. 演练应用与正式切换

数据专用 restore Compose 不会启动应用，因此不会自动消费队列或调用外站。
进一步应用演练需由运维明确配置一个隔离应用实例，连接上述恢复数据库和 Redis、
挂载 `restore-files/data`，关闭生产定时任务并限制外站出口。

启动业务之前记录 queued/running 任务和调度状态；当前后端启动会恢复任务，可能消费 queued
或将 interrupted 运行标记失败。这是可观测的状态变更，不能把启动后的数据当作原快照。
仅在隔离恢复库中，经批准后禁用示例调度任务或处理恢复队列，再运行只读与批准的写入验收。

正式灾难切换必须批准：保持旧实例只读，恢复库验收后切换网关/DNS，
观察任务结果及游标，按业务许可补采快照之后数据。数据库和 Redis 必须来自同一停写快照，
不得混入旧实例更靠前的 Redis 游标，否则可能跳过未恢复数据。

## 6. 恢复验收记录

- 备份来源、异地对象ID、解密与校验结果、快照UTC时间。
- 代码 commit、容器镜像 digest、数据库/扩展版本、迁移基线。
- PostgreSQL/Redis 导入结果，记录数与日期/游标比对，HTML 抽样结果。
- 队列恢复与调度状态、只读冒烟和批准的业务验收结果。
- 实际RTO、数据损失窗口是否满足目标RPO、未恢复部分和风险。
- 批准人、操作人、回滚/切换时间与监控观察结果。

没有实际恢复导入和计时证据时，报告必须写“恢复流程已准备，恢复演练未执行”。
