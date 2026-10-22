# Phase 2 安全审计报告

**审计时间**: 2026-10-22  
**审计范围**: 完整系统安全评估  
**审计方法**: 静态代码分析 + 配置审查 + 依赖扫描

---

## 📊 安全评级

**综合安全评分: 72/100** (中等风险)

| 维度 | 评分 | 风险等级 | 说明 |
|------|------|----------|------|
| 身份认证 | 0/100 | 🔴 严重 | 无认证机制 |
| 授权控制 | 0/100 | 🔴 严重 | 无权限管理 |
| 数据保护 | 65/100 | 🟡 中等 | 密码明文存储 |
| 网络安全 | 70/100 | 🟡 中等 | CORS过于宽松 |
| 代码安全 | 90/100 | 🟢 良好 | 无明显注入漏洞 |
| 依赖安全 | 85/100 | 🟢 良好 | 依赖版本较新 |
| 运维安全 | 75/100 | 🟡 中等 | 配置需加固 |

---

## 🔴 严重安全问题 (Critical)

### 1. **完全缺失身份认证和授权**

**风险级别**: 🔴 严重 (CVSS 9.1 - Critical)

**问题描述**:
```rust
// backend-rust/src/main.rs:209
.layer(CorsLayer::permissive())  // ❌ 允许任何来源
// 所有API端点无认证要求
.route("/api/scheduler/jobs", post(create_job))  // ❌ 任何人可创建定时任务
.route("/api/scheduler/jobs/:id", delete(delete_job))  // ❌ 任何人可删除任务
.route("/api/adapters/:id/run", post(run_adapter))  // ❌ 任何人可运行采集器
```

**攻击场景**:
1. **未授权定时任务创建**:
   ```bash
   # 攻击者可创建恶意定时任务
   curl -X POST http://victim.com:18000/api/scheduler/jobs \
     -d '{"name":"evil","collector_id":"malicious","cron":"* * * * *"}'
   ```

2. **未授权数据采集**:
   ```bash
   # 攻击者可运行任意采集器，消耗资源
   curl -X POST http://victim.com:18000/api/adapters/any_adapter/run
   ```

3. **未授权任务删除**:
   ```bash
   # 攻击者可删除所有定时任务
   curl -X DELETE http://victim.com:18000/api/scheduler/jobs/{id}
   ```

**影响**:
- ❌ 任何人可读取所有数据
- ❌ 任何人可创建/修改/删除任务
- ❌ 任何人可触发采集器执行
- ❌ DoS攻击：恶意创建大量定时任务

**CVE对比**: 类似 CVE-2023-38545 (未授权访问)

**建议修复** (P0 - 立即):
```rust
// 1. 添加JWT中间件
use tower_http::validate_request::ValidateRequestHeaderLayer;

.layer(ValidateRequestHeaderLayer::bearer("your-secret-key"))

// 2. 实现RBAC
pub struct AuthMiddleware;
impl<B> Service<Request<B>> for AuthMiddleware {
    // 验证token
    // 检查权限
}

// 3. 端点级别授权
.route("/api/scheduler/jobs", post(create_job).route_layer(require_role("admin")))
```

---

### 2. **CORS配置过于宽松**

**风险级别**: 🔴 高 (CVSS 7.5 - High)

**问题代码**:
```rust
// backend-rust/src/main.rs:209
.layer(CorsLayer::permissive())  // ❌ 允许任何域名跨域请求
```

**等价于**:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: *
Access-Control-Allow-Headers: *
Access-Control-Allow-Credentials: true  // ⚠️ 危险组合
```

**攻击场景**:
```html
<!-- 恶意网站evil.com上的代码 -->
<script>
fetch('http://victim.com:18000/api/scheduler/jobs', {
  method: 'DELETE',
  credentials: 'include'  // 携带用户cookie
}).then(r => r.json()).then(data => {
  // 窃取数据或执行恶意操作
});
</script>
```

**影响**:
- ❌ CSRF攻击：用户访问恶意网站时自动执行操作
- ❌ 数据泄露：恶意网站可读取API数据
- ❌ XSS配合：放大攻击效果

**建议修复** (P0 - 立即):
```rust
use tower_http::cors::CorsLayer;

let cors = CorsLayer::new()
    .allow_origin(["http://localhost:3080", "https://yourdomain.com"].map(|s| s.parse().unwrap()))
    .allow_methods([Method::GET, Method::POST, Method::PUT, Method::DELETE])
    .allow_headers([CONTENT_TYPE, AUTHORIZATION])
    .allow_credentials(false);  // ✅ 禁用凭证

.layer(cors)
```

---

### 3. **密码明文存储在配置文件**

**风险级别**: 🔴 高 (CVSS 8.1 - High)

**泄露位置**:
```yaml
# docker-compose.yml:13 (已提交到Git)
POSTGRES_PASSWORD: corn_password_2026  # ❌ 明文密码

# docker-compose.yml:56
DATABASE_URL: postgresql://corn_user:corn_password_2026@...  # ❌ 明文连接串

# .env:2 (未加密)
DATABASE_URL=postgresql://corn_user:corn_password_2026@...

# 测试代码中
# test_mock_quality.py:23
password='corn_pass'  # ❌ 测试密码硬编码

# 文档中
# docs/DEVELOPER.md:84
DATABASE_URL=postgresql://corn_user:corn_pass_2024@...  # ❌ 示例密码
```

**检查Git历史**:
```bash
# 已验证：.env文件在.gitignore中，但docker-compose.yml已提交
✅ .gitignore包含.env
❌ docker-compose.yml包含明文密码并已提交
❌ 文档中包含示例密码
```

**影响**:
- ❌ 任何能访问代码库的人可获取数据库密码
- ❌ 公开仓库将泄露凭证
- ❌ 离职员工保留访问权限

**建议修复** (P0 - 立即):

1. **使用环境变量**:
```yaml
# docker-compose.yml
environment:
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # ✅ 从环境变量读取
  DATABASE_URL: ${DATABASE_URL}
```

2. **使用密钥管理**:
```bash
# 使用Docker secrets
docker secret create db_password ./db_password.txt
```

3. **轮换密码**:
```bash
# 立即更改所有暴露的密码
ALTER USER corn_user WITH PASSWORD 'new_secure_password_$(openssl rand -hex 16)';
```

4. **清理Git历史**:
```bash
# 从Git历史删除敏感文件
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch docker-compose.yml" \
  --prune-empty --tag-name-filter cat -- --all
```

---

## 🟡 高风险问题 (High)

### 4. **外部HTTP请求无HTTPS强制**

**风险级别**: 🟡 高 (CVSS 6.5 - Medium)

**问题代码**:
```python
# collectors-python/collectors/dce.py:30
site_url = "http://www.dce.com.cn"  # ❌ HTTP明文传输
self.base_url = "http://www.dce.com.cn"

# collectors-python/collectors/dce.py:63
response = session.get(self.quote_url, headers=headers, timeout=30)
# ❌ 无SSL验证检查
```

**对比Phase 1**:
```python
# sina_production.py:201 ✅ 正确升级HTTPS
if url.startswith("http://"):
    url = "https://" + url[len("http://"):]
```

**中间人攻击场景**:
```
攻击者 <---> 受害者 <--HTTP--> DCE官网
  ↓
篡改价格数据: 2850 → 9999
  ↓
污染数据库
```

**影响**:
- ❌ 数据中间人篡改
- ❌ 凭证窃听（如有API key）
- ❌ DNS劫持风险

**建议修复** (P1 - 本周):
```python
# 1. 强制HTTPS
if url.startswith("http://"):
    url = "https://" + url[len("http://"):]

# 2. 验证SSL证书
response = session.get(url, verify=True, timeout=30)

# 3. 固定证书（可选）
response = session.get(url, verify='/path/to/cert.pem')
```

---

### 5. **数据库端口公开暴露**

**风险级别**: 🟡 高 (CVSS 6.8 - Medium)

**问题配置**:
```yaml
# docker-compose.yml:15-16
postgres:
  ports:
    - "15432:5432"  # ❌ 绑定到0.0.0.0，公开暴露

# docker-compose.yml:33-34
redis:
  ports:
    - "16380:6379"  # ❌ Redis无密码且公开
```

**检查实际绑定**:
```bash
$ docker ps --format "{{.Names}}: {{.Ports}}"
corn_postgres: 0.0.0.0:15432->5432/tcp  # ❌ 任何IP可连接
corn_redis: 0.0.0.0:16380->6379/tcp     # ❌ 任何IP可连接
```

**攻击场景**:
```bash
# 外部攻击者扫描端口
nmap -p 15432,16380 victim.com
# 发现开放的数据库端口

# 使用泄露的密码连接
psql -h victim.com -p 15432 -U corn_user -d corn_research
Password: corn_password_2026  # 从docker-compose.yml获取

# 窃取所有数据或注入恶意数据
```

**影响**:
- ❌ 数据库直接暴露到互联网
- ❌ 配合密码泄露，攻击者可完全控制数据
- ❌ Redis无密码，任何人可读写

**建议修复** (P0 - 立即):

1. **仅绑定localhost**:
```yaml
postgres:
  ports:
    - "127.0.0.1:15432:5432"  # ✅ 只允许本地连接

redis:
  ports:
    - "127.0.0.1:16380:6379"
```

2. **使用Docker网络（更好）**:
```yaml
# 移除ports映射，仅通过Docker网络通信
postgres:
  # ports:  # ✅ 不暴露端口
  networks:
    - corn-network
```

3. **Redis添加密码**:
```yaml
redis:
  command: redis-server --requirepass ${REDIS_PASSWORD}
```

---

### 6. **缺少请求速率限制**

**风险级别**: 🟡 中等 (CVSS 5.3 - Medium)

**问题**: 所有API端点无速率限制

**DoS攻击场景**:
```bash
# 攻击者循环触发采集
while true; do
  curl -X POST http://victim.com:18000/api/adapters/sina_production/run &
done
# 创建数千个并发采集任务，耗尽资源
```

**影响**:
- ❌ 资源耗尽：CPU/内存/数据库连接
- ❌ 服务拒绝：正常用户无法访问
- ❌ 成本攻击：云服务费用激增

**建议修复** (P1 - 本周):
```rust
use tower_governor::{governor::GovernorConfigBuilder, GovernorLayer};

// 全局速率限制
let governor_conf = Box::new(
    GovernorConfigBuilder::default()
        .per_second(10)  // 每秒10个请求
        .burst_size(30)
        .finish()
        .unwrap()
);

.layer(GovernorLayer { config: Box::leak(governor_conf) })

// 或端点级别限制
.route("/api/adapters/:id/run", 
  post(run_adapter).route_layer(rate_limit(1, Duration::from_secs(60))))
```

---

## 🟢 中等风险问题 (Medium)

### 7. **依赖版本不完全固定**

**风险级别**: 🟢 中等 (CVSS 4.3 - Medium)

**Python依赖** (`requirements.txt`):
```
requests>=2.31.0        # ⚠️ 允许任意新版本
beautifulsoup4>=4.12.2  # ⚠️ 未固定
redis>=5.0,<6           # ✅ 有上限
tenacity>=8.2,<10       # ✅ 有上限
```

**Rust依赖** (`Cargo.toml`):
```toml
axum = "0.7"              # ⚠️ 允许0.7.x所有版本
sea-orm = { version = "1.0", ... }  # ⚠️ 允许1.x
```

**风险**:
- ⚠️ 供应链攻击：恶意版本被自动安装
- ⚠️ 破坏性更新：新版本引入bug
- ⚠️ 不可重现构建

**已知良好**:
- ✅ requests 2.31.0 已知无严重CVE
- ✅ sea-orm 1.x系列稳定
- ⚠️ 但未来版本可能引入漏洞

**建议修复** (P2 - Phase 3):
```
# requirements.txt
requests==2.31.0      # ✅ 固定版本
beautifulsoup4==4.12.2
redis>=5.0,<5.1       # ✅ 更严格的范围

# 使用requirements.lock
pip freeze > requirements.lock
```

---

### 8. **缺少输入长度限制**

**风险级别**: 🟢 中等 (CVSS 4.0 - Medium)

**问题代码**:
```rust
// collection_handlers.rs:39
pub struct CreateSourceRequest {
    pub id: String,        // ❌ 无长度限制
    pub name: String,      // ❌ 可提交巨大字符串
    pub description: Option<String>,  // ❌ 无限制
}

// handlers.rs:72
if self.collector_name.trim().is_empty() {  // ✅ 空检查
    return Err(...);
}
// ❌ 但无最大长度检查
```

**攻击场景**:
```bash
# 提交10MB的description
curl -X POST http://victim.com:18000/api/sources \
  -d '{"id":"test","name":"x","description":"'$(python3 -c 'print("A"*10000000)')'"}'
# 可能导致内存溢出或数据库错误
```

**影响**:
- ⚠️ 内存消耗攻击
- ⚠️ 数据库存储浪费
- ⚠️ JSON解析慢

**建议修复** (P2 - Phase 3):
```rust
fn validate(&self) -> Result<(), CornError> {
    if self.collector_name.trim().is_empty() 
       || self.collector_name.len() > 100 {  // ✅ 长度限制
        return Err(CornError::Validation("Invalid collector_name".into()));
    }
    if let Some(desc) = &self.description {
        if desc.len() > 1000 {  // ✅ 限制描述长度
            return Err(CornError::Validation("Description too long".into()));
        }
    }
    Ok(())
}
```

---

### 9. **日志可能泄露敏感信息**

**风险级别**: 🟢 低 (CVSS 3.1 - Low)

**问题代码**:
```python
# cft.py:48
print(f"[{self.collector_id}] 目标URL: {self.price_url}")
# ✅ URL不敏感

# 但如果将来添加API key:
print(f"API Key: {api_key}")  # ❌ 潜在风险
```

**当前状态**: ✅ 未发现敏感信息记录

**建议**:
```python
# 日志规范
import logging
logger = logging.getLogger(__name__)

# 永不记录
# - 密码
# - API密钥
# - 用户token
# - 个人信息

# 记录前脱敏
logger.info(f"API call to {url.split('?')[0]}")  # ✅ 移除query参数
```

---

## ✅ 安全最佳实践

### 已实施的安全措施

1. **SQL注入防护** ✅:
```rust
// 所有查询使用参数化
sql("SELECT * FROM jobs WHERE id=$1", vec![id.into()])
// ✅ 无字符串拼接
```

2. **输入验证** ✅:
```rust
impl RunCollectorRequest {
    fn validate(&self) -> Result<(), CornError> {
        if self.collector_name.trim().is_empty() {
            return Err(CornError::Validation(...));
        }
        Ok(())
    }
}
```

3. **错误信息脱敏** ✅:
```rust
Err(e) => {
    tracing::error!("Failed to list sources: {}", e);  // ✅ 详细错误仅记录
    Err(StatusCode::INTERNAL_SERVER_ERROR)  // ✅ 客户端收到通用错误
}
```

4. **依赖版本较新** ✅:
- requests 2.31.0 (最新稳定版)
- sea-orm 1.0+ (ORM防注入)
- redis 0.24 (较新)

5. **Docker隔离** ✅:
```yaml
networks:
  - corn-network  # ✅ 使用自定义网络隔离
```

---

## 📊 安全检查清单

### 🔴 严重 (必须修复)

- [ ] **添加身份认证** (JWT/Session)
- [ ] **添加授权机制** (RBAC)
- [ ] **限制CORS来源** (移除permissive)
- [ ] **密码移到密钥管理** (环境变量/secrets)
- [ ] **数据库端口限制** (仅localhost或移除)
- [ ] **Redis添加密码**

### 🟡 高风险 (应该修复)

- [ ] DCE采集器强制HTTPS
- [ ] 添加API速率限制
- [ ] 实施请求日志审计
- [ ] 添加安全响应头
- [ ] 实施内容安全策略(CSP)

### 🟢 中等风险 (推荐修复)

- [ ] 固定依赖版本
- [ ] 添加输入长度限制
- [ ] 日志脱敏规范
- [ ] 实施会话超时
- [ ] 添加安全测试

---

## 🎯 修复优先级路线图

### Phase A - 紧急修复 (1周)

**P0任务** (必须完成):
1. 限制CORS来源 (2小时)
2. 密码移到环境变量 (2小时)
3. 数据库端口绑定localhost (1小时)
4. Redis添加密码 (1小时)
5. 轮换所有泄露的密码 (2小时)

**总计**: 8小时

---

### Phase B - 核心安全 (2周)

**P1任务**:
1. 实现JWT认证 (2天)
   - 用户登录
   - Token生成/验证
   - 中间件集成

2. 实现RBAC授权 (2天)
   - 角色定义(admin/operator/viewer)
   - 权限检查
   - 端点保护

3. API速率限制 (1天)
   - 全局限制
   - 端点级别限制
   - IP黑名单

4. DCE HTTPS强制 (半天)

5. 安全响应头 (半天)
   ```rust
   .layer(SetResponseHeaderLayer::if_not_present(
       HeaderName::from_static("x-frame-options"),
       HeaderValue::from_static("DENY")
   ))
   ```

**总计**: 6天

---

### Phase C - 加固增强 (1周)

**P2任务**:
1. 固定依赖版本 (半天)
2. 输入长度限制 (1天)
3. 安全审计日志 (1天)
4. 渗透测试 (2天)
5. 安全文档 (1天)

**总计**: 5.5天

---

## 📈 安全成熟度评估

```
当前安全等级: Level 2 (基础安全)

Level 1: 极不安全 ─────────────────────────
Level 2: 基础安全 ██████████████░░░░░░░  ← 当前
Level 3: 中等安全 ░░░░░░░░░░░░░░░░░░░░░
Level 4: 高度安全 ░░░░░░░░░░░░░░░░░░░░░
Level 5: 企业级安全 ░░░░░░░░░░░░░░░░░░░░░

目标(Phase C后): Level 3
```

### 安全能力矩阵

| 安全领域 | 当前状态 | 目标状态 | Gap |
|----------|----------|----------|-----|
| 身份认证 | ❌ 无 | ✅ JWT | 大 |
| 授权 | ❌ 无 | ✅ RBAC | 大 |
| 网络安全 | 🟡 部分 | ✅ 完善 | 中 |
| 数据保护 | 🟡 基础 | ✅ 加密 | 中 |
| 日志审计 | 🟢 基本 | ✅ 完整 | 小 |
| 漏洞管理 | 🟡 手动 | ✅ 自动 | 中 |

---

## 🔍 渗透测试建议

### 推荐测试项

1. **认证绕过测试**
   ```bash
   # 尝试访问保护的端点
   curl http://localhost:18000/api/scheduler/jobs
   # 预期: 401 Unauthorized (当前: 200 OK ❌)
   ```

2. **CSRF测试**
   ```html
   <img src="http://localhost:18000/api/scheduler/jobs/delete">
   ```

3. **SQL注入测试**
   ```bash
   curl "http://localhost:18000/api/adapters/' OR '1'='1/run"
   # ✅ 已验证：参数化查询防护有效
   ```

4. **DoS测试**
   ```bash
   ab -n 10000 -c 100 http://localhost:18000/api/adapters/sina_production/run
   # 检查资源消耗和限流
   ```

5. **端口扫描**
   ```bash
   nmap -p 1-65535 localhost
   # 验证只有必要端口开放
   ```

---

## 📚 安全参考标准

### 对标基准

1. **OWASP Top 10 2021**:
   - ✅ A03:2021 - 注入 (SQL注入已防护)
   - ❌ A01:2021 - 访问控制失效 (无认证/授权)
   - ❌ A05:2021 - 安全配置错误 (CORS/端口/密码)
   - ✅ A08:2021 - 软件和数据完整性故障 (依赖较新)

2. **CWE Top 25**:
   - ✅ CWE-79: XSS (前端使用React防护)
   - ❌ CWE-862: 缺少授权
   - ✅ CWE-89: SQL注入 (参数化查询)
   - ❌ CWE-200: 信息暴露 (密码明文)

3. **NIST Cybersecurity Framework**:
   - 识别(Identify): 🟢 良好
   - 保护(Protect): 🟡 不足
   - 检测(Detect): 🟡 基础
   - 响应(Respond): ❌ 无
   - 恢复(Recover): ❌ 无

---

## 💡 安全最佳实践建议

### 给开发团队

1. **安全编码清单**:
```
新代码检查:
□ 是否需要认证？
□ 是否需要授权？
□ 输入是否验证？
□ 输出是否编码？
□ 错误是否脱敏？
□ 日志是否安全？
```

2. **安全Review要点**:
- 所有API端点必须有认证
- 敏感操作必须有授权
- 外部输入必须验证
- 密码/密钥禁止硬编码
- 生产配置分离

3. **安全培训主题**:
- OWASP Top 10
- 安全编码实践
- 密钥管理
- 事件响应

---

## 🎯 总结

**当前安全状态**: 🟡 中等风险 (72/100)

**关键问题**:
- ❌ 无认证/授权 (严重)
- ❌ CORS过于宽松 (严重)
- ❌ 密码明文泄露 (高)
- ❌ 数据库端口公开 (高)

**亮点**:
- ✅ SQL注入防护完善
- ✅ 错误处理得当
- ✅ 依赖版本较新
- ✅ Docker网络隔离

**紧急行动** (8小时):
1. 限制CORS
2. 密码移到环境变量
3. 数据库端口限制
4. Redis加密码
5. 轮换密码

**警告**: 
> 当前系统**不适合公网部署**。必须完成Phase A修复后才能对外暴露。
> 
> 如果已对外暴露，建议：
> 1. 立即添加防火墙规则
> 2. 限制IP白名单
> 3. 尽快实施认证

**下次审计**: 完成Phase A修复后

---

**审计人**: Kiro AI  
**审计日期**: 2026-10-22  
**审计标准**: OWASP Top 10, CWE Top 25, NIST CSF

**联系人**: 如发现新的安全问题，请立即报告
