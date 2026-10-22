# 生产日志、指标与告警配置

生产入口见 [DEPLOYMENT.md](DEPLOYMENT.md)。本配置使用只读主机探针 + Prometheus textfile，
不新增公开应用 `/metrics`，不将 Docker socket 挂入监控容器。
配置存在不等于监控已部署，首次上线需完成抓取、失败注入和通知演练。

## 1. 日志配置

- Rust：生产 Compose 强制 `RUST_LOG_FORMAT=json`，stderr、UTC、无颜色；默认
  `RUST_LOG=info,sqlx=warn,sea_orm=warn`，不要常驻 debug 记录 SQL 或业务正文。
- Python：`COLLECTOR_LOG_LEVEL=INFO`，stderr UTC；stdout 专供桥接JSON，不能混入普通日志。
- 博亚文件日志：`COLLECTOR_LOG_MAX_BYTES=10485760`，`COLLECTOR_LOG_BACKUP_COUNT=5`，
  文件位于 `logs/collectors/boyar.log`，用跨进程锁串行轮转。
- 每个生产容器 Docker `json-file` 上限20 MiB × 5；监控容器上限10 MiB × 3。
  不再让主机 logrotate 同时处理这些文件。
- 日志不是审计存储，中央采集/脱敏/7天在线与30天归档须由组织日志平台落实。
  后端会捕获 Python stderr，不能承诺所有采集器日志逐行转发到容器流。

修改日志变量后重新创建对应容器；排障仅导出必要时间窗口，不导出 env、Authorization、
数据库 URL 或完整原始 HTML。示例：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs --since=15m --tail=200 backend
```

## 2. 可选指标栈

[`docker-compose.monitoring.yml`](../docker-compose.monitoring.yml) 叠加生产 Compose，
仅当指定 `monitoring` profile 才启动。Prometheus绑定本机默认19090，textfile exporter不发布端口。
Prometheus保留15天/2GB（达到任一保留限制即清理），监控数据不是业务备份。
镜像版本是示例固定版本，投产前必须扫描并替换为批准的镜像digest。

```bash
# 先准备目录，确保部署账号可写，容器UID可读。
mkdir -p monitoring/textfile
chmod 755 monitoring/textfile
python3 scripts/collect-production-metrics.py
# 任一探针失败返回1，但会原子写入失败指标；错误仅列服务名称，不输出密码。
docker compose --env-file .env.production -f docker-compose.prod.yml \
  -f docker-compose.monitoring.yml --profile monitoring config --quiet
docker compose --env-file .env.production -f docker-compose.prod.yml \
  -f docker-compose.monitoring.yml --profile monitoring up -d ops-exporter prometheus
curl --fail http://127.0.0.1:19090/-/ready
```

不要把 Prometheus无鉴权端口开放到公网；查看UI使用SSH隧道或既有受控运维网关。
探针只执行 `/health`、前端HTTP检查、Redis INFO、PostgreSQL聚合查询和本地文件/磁盘检查，
不会触发采集、写业务数据或推进游标。数据库会话强制只读且 statement_timeout=5s；
主机调用的每个子进程超时30秒。失败不会继续暴露上轮某项指标的旧数值。

## 3. 定时采集

Linux systemd示例位于 [`monitoring/systemd/`](../monitoring/systemd/)。
部署账号示例为 `corn`，路径 `/srv/corn-production`；复制前按实际机器修改。
该账号必须能读生产env和备份清单、写textfile目录、调用Docker；Docker组权限等价高权限，
仅授予专用运维账号，不授权给Web用户。

由管理员安装并启动两个unit后验证：

```bash
# 需主机管理员权限；本任务只提供模板，不自动安装。
sudo install -m 644 monitoring/systemd/corn-metrics.service /etc/systemd/system/
sudo install -m 644 monitoring/systemd/corn-metrics.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now corn-metrics.timer
systemctl list-timers corn-metrics.timer
journalctl -u corn-metrics.service --since '-10 minutes'
```

非systemd主机可用已有受控调度器每分钟调用同一脚本，禁止并发重叠执行。
脚本输出以原子rename发布，Prometheus不会读取半个文件；`corn_ops_last_collection_timestamp_seconds`
用于识别停止更新的成功旧文件。文件权限644，只含聚合值，无密码、来源URL和原始数据。

## 4. 指标清单与默认告警

| 指标 | 来源/语义 | 默认规则 |
| --- | --- | --- |
| `corn_service_up{service}` | backend存活、frontend HTTP、postgres队列表读取、redis INFO | 失败2分钟 critical |
| `corn_ops_collection_success` | 本轮所有探针与本地检查成功 | 失败2分钟 warning |
| `corn_ops_last_collection_timestamp_seconds` | 本轮主机采集时间 | 缺失/超过180秒，持续3分钟 critical |
| `corn_async_queued_jobs` / `corn_async_running_jobs` | async_jobs按状态计数 | 展示趋势 |
| `corn_async_oldest_queued_age_seconds` | 最早queued的created_at到当前时间 | 超过900秒持续5分钟 warning |
| `corn_async_oldest_running_age_seconds` | 最早running的started_at（缺失用created_at）到当前时间 | 超过1800秒持续5分钟 warning |
| `corn_redis_memory_used_ratio` | used_memory / maxmemory | 超过80%持续10分钟 warning |
| `corn_disk_used_ratio` | 部署目录所在文件系统磁盘使用率 | 超过80%持续10分钟 warning |
| `corn_backup_last_success_timestamp_seconds` | 本地非incomplete目录manifest的修改时间，无备份为0 | 超过26小时持续10分钟 critical |
| Prometheus `up{job="corn-ops"}` | exporter抓取状态 | 失败2分钟 critical |

告警阈值是初始建议，不是SLA；按真实采集耗时/维护窗口校准。Redis采用noeviction，
内存耗尽会拒绝写入而非淘汰游标，必须提前扩容/清理经批准的非游标数据。
备份时间指标不验证manifest内容，不证明异地备份、备份任务刚刚成功或恢复可用；
成功判断以备份脚本、verify-backup和异地验证/恢复演练记录为准。复制目录可能改变mtime，
正式接入组织备份平台时应使用其可信作业完成时间。

## 5. 未覆盖项与上线前补齐

当前探针未提供HTTP p95/QPS/5xx、主机CPU/内存、磁盘inode、PostgreSQL连接池/复制延迟、
证书到期和真实数据源新鲜度指标，不宣称这些已配置。应接入现有主机agent、
Nginx日志分析、数据库监控及外部TLS检查。建议初始门限：5xx超过5%持续5分钟、
内存超过80%持续10分钟、证书剩余少于14天；各指标需先确认采集口径与负载基线。
`/health`仅存活探针，不代表真实采集或业务正确性。

规则见 [`monitoring/alerts.yml`](../monitoring/alerts.yml)，Prometheus发现告警不代表消息已发送。
投产前在 `prometheus.yml` 配置组织Alertmanager地址、网络/TLS/凭据，Alertmanager中配置
值班通知路由与接收人，凭据放密钥管理系统，禁止写入仓库。此处不提供虚构通知地址。
维护窗口配置有截止时间的silence，维护后确认采集恢复及告警解除。

## 6. 验证

本地离线单元测试：`python3 -m unittest discover -s tests/ops -v`。
启动监控后在Prometheus查询 `up{job="corn-ops"}`、`corn_ops_collection_success` 和各指标。
在隔离环境分别模拟服务失败、采集器停止超过3分钟、旧备份以及Redis接近限额，
检查规则进入pending/firing/恢复，并测试Alertmanager确实通知值班人。
不能为测试磁盘告警把生产盘写满，也不能对生产执行FLUSHALL。
