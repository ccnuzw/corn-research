# Phase 2 生产部署指南

适用版本：`v2.0.0-phase2`。本文以仓库中的 `docker-compose.prod.yml` 为权威部署入口，
不使用开发用 `docker-compose.yml` 或旧版 `scripts/deploy.sh`。
备份和恢复的权威流程见 [BACKUP_STRATEGY.md](BACKUP_STRATEGY.md)。
本指南是部署操作手册，不表示生产实机验收已经完成；本轮验证记录见
[reports/PHASE2_RELEASE_VALIDATION.md](reports/PHASE2_RELEASE_VALIDATION.md)。

## 1. 部署架构与上线边界

```text
操作者浏览器 -> VPN/防火墙 -> Nginx TLS + Basic Auth
                          /         -> frontend:3000 (Next.js production)
                          /backend/ -> backend:8000 (Rust + Python)
                                        -> postgres:5432
                                        -> redis:6379 (游标/锁/通知)
```

- 单机单实例部署；后端内部固定两个异步 worker，并运行定时任务。
  启动恢复会协调未完成运行，禁止直接扩容多个后端实例，否则可能误处理其他实例运行。
- PostgreSQL 16、Redis 7 使用独立持久卷；生产 Compose 不映射数据库/Redis 主机端口。
  迁移目前不依赖 TimescaleDB 扩展，新环境使用普通 PostgreSQL；
  已有 TimescaleDB 实例必须保留兼容的 TimescaleDB 镜像，不能将其卷直接挂到普通 PostgreSQL。
- 后端和前端调试端口只绑定 `127.0.0.1`；默认网关也只绑定本机。
- **应用目前没有用户身份、RBAC 或审计权限体系，CORS 为 permissive。**
  Basic Auth 仅是可信团队的临时网关保护，不是多租户鉴权；账号持有者拥有全部 API 权限。
  不得将裸 API 暴露到公网；正式对外服务前须完成应用鉴权、安全评审及依赖漏洞审查。
- 示例镜像使用主版本/发行版标签，并非不可变摘要；正式投产前固定经扫描批准的镜像 digest，
  在发布记录保存 digest 和构建产物。仓库锁文件只能固定应用依赖，不能固定基础镜像。
- 历史 Mock 压测报告不能证明真实来源可用性或容量，禁止据此宣称生产 SLA。

## 2. 环境要求

建议初始资源：Linux x86_64/ARM64、4 vCPU、8 GB RAM、100 GB SSD，按 HTML 存档增长调整。
这是初始配额建议，不是经过长期压测的容量承诺。

安装 Git、Docker Engine、Docker Compose v2+、Python 3、OpenSSL、`htpasswd`（apache2-utils）。
构建阶段需要访问镜像仓库、crates.io、npm、PyPI，以及 Next.js 当前引用的 Google Fonts；
运行阶段需要访问博亚、新浪、大商所官方站点。没有外网的环境应提前准备镜像和字体。
主机统一使用 NTP，容器记录 UTC；定时表达式按 UTC 执行。

```bash
docker version
docker compose version
git --version
python3 --version
df -h
```

只开放经批准的 SSH/VPN 和 HTTPS 入口；Docker 端口发布可能绕过部分主机防火墙规则，
需在云安全组和 Docker 网络规则同时验证。不要在部署过程中运行 `down -v`、`volume prune`。

## 3. 生产环境变量

在独立部署目录工作，不要覆盖正在运行的开发目录：

```bash
git clone https://github.com/ccnuzw/corn-research.git corn-production
cd corn-production
git switch --detach v2.0.0-phase2
cp .env.production.example .env.production
chmod 600 .env.production
openssl rand -hex 32
# 将上一步输出填入 .env.production 的 POSTGRES_PASSWORD；不要将输出写入工单或日志。
mkdir -p data logs/collectors backups nginx/ssl
chmod 700 backups nginx/ssl
```

`.env.production` 由 Compose 的 `--env-file` 读取，**不要 `source` 它**。
每条运维命令都必须使用同一项目名、文件及 env 文件，避免连到开发实例或新建错误卷。

| 变量 | 说明 |
| --- | --- |
| `COMPOSE_PROJECT_NAME` | 默认 `corn-production`；修改会切换卷/网络命名空间，不是数据迁移 |
| `RELEASE_VERSION` | 本地构建镜像标签；升级时更换，保留上一版本镜像 |
| `POSTGRES_DB` / `POSTGRES_USER` | 新数据库初始化名称；建议只用字母、数字、下划线 |
| `POSTGRES_PASSWORD` | 必填，建议 64 位十六进制，避免 URL 特殊字符转义；无内置生产默认值 |
| `BACKEND_PORT` / `FRONTEND_PORT` | 默认 `18000` / `3080`，只绑定本机 |
| `NEXT_PUBLIC_API_URL` | 默认 `/backend`，由 Nginx 转发；**构建时**写入 JS，改后必须重建前端 |
| `HTTPS_BIND` / `HTTPS_PORT` | 默认 `127.0.0.1:8443`；上线后才按 VPN/防火墙策略调整 |
| `RUST_LOG` | 默认 `info,sqlx=warn,sea_orm=warn`；避免生产 SQL/debug 噪声和敏感数据 |
| `RUST_BACKTRACE` | 默认 `0`，排障短时设置 `1` 后需重新创建容器 |
| `COLLECTOR_LOG_LEVEL` | DEBUG/INFO/WARNING/ERROR/CRITICAL，默认 INFO |
| `COLLECTOR_LOG_MAX_BYTES` | 博亚单文件轮转大小，默认 10485760（10 MiB） |
| `COLLECTOR_LOG_BACKUP_COUNT` | 博亚历史轮转数量，默认 5 |
| `BOYAR_START_ARTICLE_ID` / `BOYAR_SCAN_LIMIT` | 无游标时扫描起点及范围，不覆盖已提交的增量游标 |
| `SINA_FUTURES_SYMBOLS` | 默认 `nf_C0`，逗号分隔；不要填写内部 Docker 域名作浏览器 API 地址 |
| `DCE_CONTRACTS` / `DCE_START_DATE` / `DCE_MAX_DAYS` | 官方合约筛选、首次采集起点、最大日期跨度；空值使用采集器默认逻辑 |

后端 `SERVER_PORT=8000`、`RUST_LOG_FORMAT=json`、内部数据库/Redis URL 由生产 Compose 设置。
PostgreSQL 内部连接示例使用 `sslmode=disable`，仅适用于本机受控 Docker bridge。
跨主机/托管数据库须修改连接为 `sslmode=verify-full` 并配置 CA；不要沿用明文配置。
Redis 内部未配置密码，只允许受控网络访问；跨主机必须另配 TLS/ACL 并更新所有客户端。

生产密码修改不会自动更新已有 PostgreSQL 卷中的角色密码；必须在维护窗口修改数据库角色、
env 文件和备份密钥记录，再重新创建应用容器。`.env.production`、私钥、htpasswd、备份均禁止提交。

## 4. 配置 TLS 与网关登录

将有效证书链及私钥放入以下位置（证书 SAN 必须匹配访问域名）：

```text
nginx/ssl/fullchain.pem
nginx/ssl/privkey.pem
nginx/htpasswd
```

```bash
htpasswd -cB nginx/htpasswd operator
chmod 600 nginx/htpasswd nginx/ssl/privkey.pem
```

后续新增账号不要再用 `-c`，否则会覆盖现有账号文件。安排证书自动续期和过期告警，续期后执行
`dc exec nginx nginx -s reload`。不要在生产使用 `curl -k` 跳过证书校验。
对于隔离演练环境可使用自签证书，但客户端必须显式信任演练 CA，不得当成生产证书。

下文在 Bash 中定义命令简写：

```bash
dc() { docker compose --env-file .env.production -f docker-compose.prod.yml "$@"; }
dc --profile gateway config --quiet
# 不要将完整 config 输出上传：其中可能包含数据库连接密码。
```

## 5. 首次部署（全新数据库）

```bash
dc build backend frontend
# 镜像构建失败即停止，不绕过类型检查、不把失败版本打成已验收。
dc up -d postgres redis
dc ps
dc logs --tail=100 postgres
```

PostgreSQL 官方入口只在 **空卷** 时按文件名顺序执行 `migrations/001` 到 `010`。
`pg_isready` 健康不能替代迁移验证；检查初始化结束和关键表后再启动应用。

```bash
dc exec -T postgres sh -ec 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "SELECT to_regclass('\''public.async_jobs'\''), to_regclass('\''public.scheduled_jobs'\''), to_regclass('\''public.collection_records'\'');"'
dc up -d backend frontend
dc ps
curl --fail http://127.0.0.1:18000/health
dc --profile gateway up -d nginx
dc exec nginx nginx -t
```

网关本地默认监听 8443。将 DNS 指向服务器或通过 SSH 隧道访问，同时保证证书域名正确。
设定示例环境变量后验证（curl 会提示输入密码）：

```bash
export DEPLOY_HOST=corn.example.com
curl --fail --user operator "https://${DEPLOY_HOST}:8443/backend/health"
curl --fail --user operator "https://${DEPLOY_HOST}:8443/backend/api/sources"
curl --fail --user operator "https://${DEPLOY_HOST}:8443/backend/api/data/latest?limit=5"
# 无凭据请求应该返回 401；浏览器登录后检查 Dashboard、数据源管理、采集历史。
curl -I "https://${DEPLOY_HOST}:8443/"
```

确认安全和业务验收后，才在 `.env.production` 修改网关监听地址/端口，并重新创建 nginx。
若前端通过 3080 直接打开，默认 `/backend` 不会代理到后端；应从 TLS 网关进入。

## 6. 既有数据库升级

**重要：仓库没有自动 schema 版本登记器。** `scripts/migrate_db.sh` 仅覆盖早期两张表，
不得用于 Phase 2 完整升级。迁移含触发器/DDL，不能盲目从 001 重跑。

1. 记录当前 commit、镜像 ID、数据库版本、已应用迁移；在克隆数据库演练升级。
2. 阻断网关新流量，等待队列和运行收敛；停止 backend 和其他数据库/Redis 写入者。
3. 按备份策略生成一致性备份并复制异地；保留旧镜像及环境文件的加密副本。
4. Phase 1 已确认应用 001–008 的环境，仅应用 009、010（其他基线须逐项审核）。

```bash
dc stop nginx frontend backend
bash scripts/backup-production.sh
# 仅适用于已确认 001-008 完整应用的基线：
for migration in migrations/009_async_jobs.sql migrations/010_dce_corn_prices.sql; do
  dc exec -T postgres sh -ec 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' < "$migration" || break
done
# 任一迁移出错即停止，检查状态，不继续启动应用。
```

使用 `set -e` 的发布脚本或逐条执行并检查返回值；`break` 后必须判定两条均成功再进入下一步。
核验索引/表结构并在发布记录登记迁移文件校验值，随后重新构建/启动服务和冒烟验证。
全新卷自动初始化中途失败时，不要反复重启当成重试：入口不会重新跑已创建卷的初始化脚本。
先查明已完成 SQL，再在隔离实例恢复或重建确认无业务数据的新卷。

## 7. 功能验收与定时任务

- `/health` 是进程级存活检查，不是持续数据库/来源就绪检查；同时测试数据查询和实际任务结果。
- 异步采集推荐 `POST /api/collectors/run/async`，轮询 `GET /api/jobs/:id`；具体字段见 [API.md](API.md)。
  同步采集可能耗时数分钟，不要靠缩短网关超时判断采集失败。
- 真实来源请求会写入数据、推进游标并访问外站，必须获运维批准；首次在隔离环境验收，
  不在正式生产直接运行写入型测试/压测，也不要以 Mock 成功代替真实来源验收。
- 检查 `collection_runs`、`async_jobs`、去重结果、HTML 存档及 Redis 游标；数据持久化成功后才能推进游标。
- 008 中两条示例定时任务默认禁用；审核 UTC cron 和来源限速后，通过调度 API 单独启用。
  北京时间 08:00 对应 `0 0 0 * * *`（秒、分、时、日、月、周）。
- 重启时进行中任务可能标记失败，queued 任务会被恢复消费；不要删除运行记录或锁来“修复”。
  等待持有者退出、核实锁 TTL 和幂等入库后再重试。

## 8. 生产日志与监控

| 来源 | 位置/格式 | 轮转 |
| --- | --- | --- |
| Rust tracing | 容器 stderr，JSON，UTC，无 ANSI | Docker `json-file` 每文件 20 MiB × 5 |
| Python 通用采集日志 | stderr，UTC 文本；stdout 专供桥接 JSON | 同上 |
| 博亚文件日志 | `logs/collectors/boyar.log`，UTC，跨进程锁轮转 | 默认 10 MiB ×（当前 1 + 历史 5） |
| Nginx | stdout/stderr，仅方法和路径，不记录 query/Authorization | Docker 同上 |

`RUST_LOG`、采集日志级别修改后用 `dc up -d --force-recreate backend` 应用。
不再对 Docker 日志文件直接配置主机 logrotate，不同时用外部轮转处理 boyar.log。
容器轮转日志是短期诊断，不是持久审计；由运维采集到受控日志平台，建议在线 7 天/归档 30 天。
后端会捕获 Python stderr，部分上下文可能只在任务错误/数据库运行记录中出现，不承诺逐行中央日志转发。

```bash
dc logs --since=30m --tail=300 backend
dc logs --since=30m --tail=100 nginx postgres redis
dc stats --no-stream
# 若 Compose 版本不支持 stats，使用 docker stats --no-stream。
du -sh logs data backups
```

严禁记录 `.env.production`、完整数据库 URL、Authorization、原始敏感 HTML；日志导出先脱敏。
HTML 及 original_text 可能含来源内容，按最小权限和数据授权控制访问。
部署运维至少配置：磁盘 >80%、内存 >80%、服务 unhealthy、备份失败/超过 26 小时未完成、
证书剩余 <14 天、5xx 持续上升和任务长期 queued/running 告警。阈值是初始建议，须按真实采集耗时校准。
仓库当前没有 Prometheus/自动告警服务，上述必须由外部平台接入，不能视为已部署。

## 9. 故障排查手册

先记录时间、commit、任务 ID、请求路径与脱敏错误，再定位，不先重启/清库。

| 现象 | 检查 | 处理 |
| --- | --- | --- |
| Compose 提示缺少密码 | `--env-file` 路径和 POSTGRES_PASSWORD | 填写生产 env；不要打印密码或使用开发默认密码 |
| backend unhealthy / 404 | `/health`、内部 8000 端口、容器日志 | 不使用旧 `/api/health`；检查 SERVER_PORT 与映射 |
| 数据库 password authentication failed | 卷是否早已初始化、角色密码 | 环境变量不会改旧密码，按维护流程轮换角色密码 |
| relation async_jobs does not exist | 迁移基线和 SQL 错误日志 | 停后端，备份后补跑缺失迁移；不盲目重跑 001 |
| Redis OOM / cursor 失败 | `dc exec redis redis-cli INFO memory` | noeviction 会拒绝写，评估扩容并排查通知增长；不要 FLUSHALL |
| 502 | 后端/前端健康、Nginx upstream | 修复目标服务；重建容器后必要时 reload nginx 重新解析 DNS |
| 401 | htpasswd、账号、TLS 入口 | 使用授权账号；不删除 auth_basic 绕过登录 |
| 429 | 网关访问频率、轮询间隔 | 降低请求频率/指数退避；不无上限提高 burst |
| 浏览器请求 localhost/backend 域名 | NEXT_PUBLIC_API_URL 构建值 | 设为 `/backend` 并重建前端；浏览器不能解析 Docker 服务名 |
| Next 构建失败 | type-check/lint、npm 锁文件、字体网络 | 修复构建错误；不忽略 TS/lint 强行发布 |
| Rust --locked 构建失败 | Cargo.lock 是否入库、manifest 是否匹配 | 在开发环境更新并审查锁文件，禁止生产临时放开依赖版本 |
| Rust macOS libxcrun 架构错误 | Xcode Command Line Tools 与进程架构 | 修复本机工具链或使用 Linux 构建，不代表业务测试通过 |
| 外站 403/429、日期/表格解析失败 | 采集错误、HTML 存档和官方页面 | 保留证据、限速退避、更新解析器；禁止回退合成数据或用今日日期伪装 |
| 任务 409 / 一直 running | `GET /api/jobs/:id`、运行历史、Redis 锁 | 查现有任务，等完成或按恢复流程处理；不并发重复触发 |
| HTML/日志写入失败 | 挂载路径、磁盘空间、权限 | 修复目录权限/容量，禁止 chmod 777 全目录 |
| 健康检查正常但无数据 | 实际 SQL 查询、定时任务 enabled、来源错误 | 进程存活不等于采集成功；检查任务结果与游标 |

## 10. 回滚与发布记录

升级前保存旧 commit、镜像和一致性备份。应用回滚仅适用于数据库向后兼容：
切换旧版本/镜像，使用该版本的 Compose 与 env，重新启动并验收。
不能通过 Git 回退撤销 SQL。需要数据库回滚时，在独立卷恢复整套数据库、Redis、HTML，
验收后切换入口，明确维护期间新数据的丢失范围；流程见备份策略。
禁止对在用生产卷运行 `pg_restore --clean`，禁止 `git reset --hard` 覆盖运行目录。

发布记录至少包含：操作者/批准人、UTC 时间、commit/tag、基础镜像及应用镜像 ID、
迁移基线/校验值、备份位置/校验/异地副本、构建和冒烟命令结果、已知风险、回滚负责人。
生产门禁：TLS/网关权限验证、真实来源验收、恢复演练、依赖扫描、监控告警和留存策略均由运维签字。
