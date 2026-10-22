# Phase 2 数据备份与恢复策略

生产 Compose、访问边界和环境变量以 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) 为准。
本文定义策略与可执行步骤，不宣称已经完成异地备份或生产恢复演练。

## 1. 目标与数据清单

初始目标：每日维护窗口一致性快照，RPO ≤24 小时、RTO ≤4 小时。
这是运维目标，只有演练计时和监控达标后才能承诺；若业务不接受每日停写，须建设
PostgreSQL WAL 连续归档/PITR、Redis 持久化及跨存储一致性机制，而不是声称已有零停机备份。

| 数据 | 权威位置 | 备份方式 |
| --- | --- | --- |
| RAW/STANDARD、适配器、运行历史、定时任务、异步队列 | PostgreSQL 卷 | `pg_dump -Fc --no-owner --no-acl` |
| 增量游标、锁、通知 | Redis 卷 | 停写时 `redis-cli --rdb`，AOF 不是异地备份 |
| 原始 HTML 等采集文件 | 主机 `data/` | 同一停写窗口 tar.gz |
| 版本/产物 | Git + 镜像 | commit、image ID；镜像推受控仓库或单独导出 |
| env、证书、网关密码文件 | 部署主机/密钥系统 | 单独加密保管；不放普通备份或 Git |
| 诊断日志 | Docker/`logs/` | 独立日志平台按保留策略归档，不与数据库事务一致性绑定 |

SQL 数据先提交、游标后推进；分别在不同时间备份会造成跳数或重采风险。
因此必须停掉后端 worker、调度器、手工 Python 程序及其他写入客户端。
仅阻断 HTTP 入口或暂停定时任务不足以形成一致性备份。

## 2. 执行备份

需安装 Docker Compose、Python 3、tar、Git。使用部署账号运行，备份目录权限 0700，文件 0600。
脚本不读取 shell env 内容，不打印连接密码；支持 `ENV_FILE`、`BACKUP_DIR`。

```bash
cd /srv/corn-production
dc() { docker compose --env-file .env.production -f docker-compose.prod.yml "$@"; }
# 通知维护窗口；阻断入口并确认不再接受新任务。
dc stop nginx frontend
# 等现有 async_jobs/collection_runs 收敛，再停止 backend；确认其他写入者也已停止。
dc stop backend
bash scripts/backup-production.sh
# 返回0且出现 Backup complete 才视为本地快照完成。
# 本地校验、加密、异地复制和抽样可读性检查完成后恢复服务。
dc up -d backend frontend
dc --profile gateway up -d nginx
```

脚本串行锁位于 `backups/.backup-lock`；非正常退出后可能残留，检查确无运行任务后由运维清理，
不要无条件删锁。失败产物保留在 `.incomplete-*`，无 manifest 的目录不能用于正式恢复。
脚本会在后端运行时拒绝备份，但**不能探测外部手工写入者**，停写仍是操作人的责任。
PostgreSQL 与 Redis 必须保持运行，Redis 以复制协议生成独立 RDB 文件，不停止 AOF。

成功目录包含：

```text
postgres.dump
redis.rdb
html-data.tar.gz
code-version.txt
image-ids.txt
manifest.json             # 每个文件的 SHA-256
```

脚本不自动恢复服务、不自动删除旧备份。这样避免失败后自动恢复写入覆盖排障现场；
值班人员必须在成功/失败两种路径确认业务恢复。日常自动化应将完整维护流程放到受控调度器，
每日 UTC 02:00（北京时间10:00，可按业务调整），失败即告警，不能仅把停写脚本单独塞进 cron。

校验文件完整性（BACKUP 指向本次成功目录）：

```bash
export BACKUP=/srv/corn-production/backups/20261022T020000Z-12345
python3 - "$BACKUP" <<'PY'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
for name, expected in json.loads((root / 'manifest.json').read_text()).items():
    digest = hashlib.sha256()
    with (root / name).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise SystemExit('Checksum mismatch: ' + name)
print('All checksums match')
PY
# pg_restore -l 验证目录可读取，不等于完整恢复已验证。
dc exec -T postgres pg_restore --list < "$BACKUP/postgres.dump" > /dev/null
tar -tzf "$BACKUP/html-data.tar.gz" > /dev/null
```

## 3. 异地、加密和留存

采用 3-2-1：生产数据 + 本地快照 + 独立账号/区域的异地加密副本，至少一份不可变存储。
使用组织批准的 KMS/age/GPG 工具加密；密钥与备份分开管理，禁止将私钥或密码写进脚本。
上传完成后从异地下载验证解密和 manifest，再记录对象 ID、时间、校验结果及操作者。
本地磁盘和同机 Docker 卷不算异地备份，RAID、Redis AOF 和 PostgreSQL 副本都不能替代备份。

建议留存：本地7份每日、异地30份每日、12份月度；按数据授权和合规要求最终批准。
过期删除须确认异地成功和最新恢复演练通过，使用受控生命周期规则；本脚本不实现自动清理。
容量按数据库 dump + HTML 总量 × 留存份数估算，预留两次全备空间，磁盘80%告警。

## 4. 恢复演练（隔离环境）

至少每月、每次重大迁移前演练，禁止直接覆盖在用生产数据。
恢复要与备份的 PostgreSQL 主版本兼容；包含 TimescaleDB 时使用相同扩展版本镜像。
不要将 PG16 数据目录直接给其他主版本启动。

1. 验证异地下载包、解密和校验值，查阅 code-version、镜像及迁移记录。
2. 准备独立机器/工作目录、独立 `.env.restore`，复制生产 env 后更换强密码、端口及
   `COMPOSE_PROJECT_NAME=corn-restore`。密钥文件权限600。
3. **在启动数据库前**，在隔离副本的 Compose 删除 postgres 的
   `./migrations:/docker-entrypoint-initdb.d:ro` 挂载。恢复 dump 不能先初始化一套相同业务表。
   保留原生产文件不变，不启动后端/网关，不使用生产卷。
4. 定义 `restore_dc`，仅启动 postgres、redis；确认是新的隔离卷。

```bash
restore_dc() { docker compose --env-file .env.restore -f docker-compose.restore.yml "$@"; }
restore_dc up -d postgres redis
# 在全新的空业务数据库恢复；遇错停止，禁止用 --clean 直接覆盖生产。
restore_dc exec -T postgres sh -ec \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl --exit-on-error' \
  < "$BACKUP/postgres.dump"
```

Redis 默认会优先载入 AOF，因此恢复 RDB 时必须使用空 Redis 数据目录，不能只把 dump.rdb
复制进含旧 appendonlydir 的卷。在隔离环境执行：

```bash
restore_dc stop redis
# 确保这是 NEW restore 卷，不是生产卷；先只读检查目录应为空。
restore_dc run --rm --no-deps --entrypoint sh redis -ec 'ls -la /data'
# 将RDB通过一次性Redis服务容器写入挂载卷，不需要识别主机卷路径：
restore_dc run --rm -T --no-deps --user root --entrypoint sh redis \
  -ec 'test ! -e /data/appendonlydir && test ! -e /data/dump.rdb; cat > /data/dump.rdb; chown redis:redis /data/dump.rdb' \
  < "$BACKUP/redis.rdb"
# 如果目录不为空，停止并重新准备全新的隔离卷；不要在生产目录执行 rm。
restore_dc up -d redis
```

注意：前述启动 Redis 会产生 AOF 目录，因而正式恢复操作应在全新 Redis 卷上、
**第一次 Redis 服务启动前**先运行写入 RDB 的一次性容器；上方 `test` 正是防止覆盖已有卷的保护。
已启动过 Redis 的演练卷应换一个新的恢复项目名并只启动 postgres，再写入 Redis RDB。

解包 HTML 前用 `tar -tzf` 审查可信备份内容，再在隔离目录解包：

```bash
tar -xzf "$BACKUP/html-data.tar.gz" -C /srv/corn-restore
```

5. 在不启动业务进程时核验表、记录数、最新业务日期、关键游标、去重索引和 HTML 文件。
   恢复 RDB 可能含锁；确认原持有者不存在并等待 TTL，禁止随意删游标。
6. 克隆环境出站受限，核验/禁用恢复出的启用定时任务；启动后端可能自动消费 queued 任务并
   将 interrupted 运行标记失败，因此先检查 `async_jobs`、`collection_runs`、`scheduled_jobs`。
   这类恢复状态变更需留证，并确保不会触发真实生产采集。
7. 使用备份对应的代码镜像启动隔离应用，运行只读冒烟和批准的隔离采集验证。
   验证数据/游标一致、去重无丢失、历史可查询后，记录 RTO、实际数据损失窗口和结果。

## 5. 真正灾难切换

由事件指挥批准，冻结旧实例写入，宣布从哪个快照恢复及预期丢失范围。
按演练流程恢复到新环境，必要时补采快照之后数据，不直接复用旧 Redis 的较新游标。
验证通过后切换 DNS/网关，持续观察错误率和队列；保留旧数据只读以供追溯。
记录恢复开始/完成时间、备份 ID、checksum、commit、记录数、游标比对和负责人。
每月将演练报告存入受控运维系统；密码、备份内容和个人信息不提交 Git。
