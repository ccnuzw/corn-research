# Phase 2 数据备份与恢复策略

生产 Compose、访问边界和环境变量以 [DEPLOYMENT.md](DEPLOYMENT.md) 为准。
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
BACKUP_MAINTENANCE_CONFIRMED=1 bash scripts/backup-production.sh
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
backup-metadata.json      # UTC 完成时间和停写确认
manifest.json             # 每个文件的 SHA-256
```

脚本不自动恢复服务、不自动删除旧备份。这样避免失败后自动恢复写入覆盖排障现场；
值班人员必须在成功/失败两种路径确认业务恢复。日常自动化应将完整维护流程放到受控调度器，
每日 UTC 02:00（北京时间10:00，可按业务调整），失败即告警，不能仅把停写脚本单独塞进 cron。

校验文件完整性（BACKUP 指向本次成功目录）：

```bash
export BACKUP=/srv/corn-production/backups/20261022T020000Z-12345
python3 scripts/verify-backup.py "$BACKUP"
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

## 4. 恢复流程

唯一操作流程见 [RESTORE_GUIDE.md](RESTORE_GUIDE.md)。使用独立的
[docker-compose.restore.yml](../docker-compose.restore.yml)，其数据卷名称与生产不同，
不含初始化迁移、业务进程和公开端口。

恢复必须先向全新 Redis 卷写入 RDB，再首次启动 Redis，避免 AOF 优先载入覆盖快照。
生产业务始终不得直接对在用卷执行覆盖恢复。每月及重大迁移前至少演练一次。

## 5. 真正灾难切换

由事件指挥批准，冻结旧实例写入，宣布从哪个快照恢复及预期丢失范围。
按演练流程恢复到新环境，必要时补采快照之后数据，不直接复用旧 Redis 的较新游标。
验证通过后切换 DNS/网关，持续观察错误率和队列；保留旧数据只读以供追溯。
记录恢复开始/完成时间、备份 ID、checksum、commit、记录数、游标比对和负责人。
每月将演练报告存入受控运维系统；密码、备份内容和个人信息不提交 Git。

## 6. 自动化边界与验收

脚本通过停写确认、后端运行检查、pg_restore目录检查、Redis RDB检查和SHA-256校验
形成一份本地快照。SHA-256不能证明数据库业务完整，也不能证明备份者身份，
正式归档还需受控存储、签名/访问控制和真实恢复演练。

监控中的本地备份时间只表示出现带manifest的成功目录，不能证明异地上传或恢复通过。
异地上传与保留期删除由组织备份平台执行，本仓库不假装已经配置云凭据和自动上传。
