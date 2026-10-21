# 消息通知与消息队列评估

**评估对象**: 统一消息通知系统 + 消息队列

---

## 📬 统一消息通知系统

### 需求分析

#### 使用场景
```
1. 采集完成通知
   "博亚采集完成，获取3条新数据"
   
2. 采集失败告警
   "博亚采集失败：网络超时"
   
3. 数据异常告警
   "检测到山东到车量异常波动：-50%"
   
4. 定时任务通知
   "每日采集任务已启动"
   
5. 系统状态通知
   "数据库连接失败"
```

#### 通知渠道
```
当前阶段：
- Web端实时通知（WebSocket）
- 邮件（可选）
- Telegram（可选）

未来扩展：
- 微信
- 钉钉
- 飞书
```

---

### 方案评估

#### 方案A：简化版（推荐） ⭐⭐⭐⭐⭐

##### 技术栈
```toml
# 无需新增依赖
# 使用已有组件：
- Axum WebSocket (已有)
- Redis Pub/Sub (Redis已有)
```

##### 实现方案
```rust
// 1. 通知结构
#[derive(Serialize)]
struct Notification {
    id: Uuid,
    level: Level,      // Info/Warning/Error
    title: String,
    message: String,
    timestamp: DateTime<Utc>,
}

// 2. Redis Pub/Sub（无需额外依赖）
async fn publish_notification(notif: &Notification) {
    redis.publish("notifications", serde_json::to_string(notif)?).await?;
}

// 3. WebSocket推送（Axum已支持）
async fn ws_handler(ws: WebSocket, state: AppState) {
    let mut pubsub = state.redis.subscribe("notifications").await?;
    
    while let Some(msg) = pubsub.on_message().next().await {
        let notif: Notification = serde_json::from_str(&msg)?;
        ws.send(serde_json::to_string(&notif)?).await?;
    }
}

// 4. API接口
GET /api/notifications      // 获取历史通知
POST /api/notifications/mark-read  // 标记已读
```

##### 优点
```
✓ 零新增依赖
✓ 实现简单（~100行）
✓ 实时推送
✓ 支持历史查询
✓ 够用
```

##### 缺点
```
✗ 不支持邮件等外部渠道（当前不需要）
✗ 无持久化（可用PostgreSQL存储）
```

##### 代码量
```
~150行（含WebSocket + Redis Pub/Sub + API）
```

---

#### 方案B：完整版（不推荐）

##### 技术栈
```toml
# 需要新增
lettre = "0.11"          # 邮件
teloxide = "0.12"        # Telegram
tokio-tungstenite = "0.21"  # WebSocket（Axum已有）
```

##### 缺点
```
✗ 新增3个依赖
✗ 代码量大（~500行）
✗ 配置复杂
✗ 当前用不到
```

---

### 推荐：方案A（简化版）

#### 理由
```
1. ✓ 零新增依赖（用Redis + Axum）
2. ✓ 满足核心需求（Web端实时通知）
3. ✓ 代码量少（150行）
4. ✓ 易于扩展（未来加邮件/Telegram）
```

#### 实施优先级
```
阶段1（明天）：
- WebSocket实时推送
- Redis Pub/Sub
- 基础通知API

阶段2（未来按需）：
- 邮件通知
- Telegram通知
- 通知规则配置
```

---

## 📨 消息队列

### 需求分析

#### 当前系统特点
```
采集特点：
- 每天多次采集
- 单次10-100条
- 采集耗时：30-60秒
- 并发压力：低
- 失败重试：需要

数据流：
Python采集器 → Rust → PostgreSQL
```

#### 是否需要队列？

##### 场景1：采集任务调度
```
问题：多个采集器同时运行会不会冲突？

分析：
- 当前：每天固定时间采集（8:00）
- 采集器：3个（Mock, 博亚, 新浪）
- 并发：低（可以串行执行）

结论：不需要队列
方案：定时任务串行执行即可

async fn run_daily_collection() {
    run_collector("boyar_v2").await?;
    run_collector("sina_v2").await?;
    run_collector("mock").await?;
}
```

##### 场景2：失败重试
```
问题：采集失败需要重试怎么办？

分析：
- 失败率：低（网络问题偶发）
- 重试策略：简单（3次重试）
- 延迟要求：不严格（1小时内重试即可）

结论：不需要队列
方案：定时任务内重试即可

async fn run_with_retry(collector_id: &str) -> Result<()> {
    for attempt in 1..=3 {
        match run_collector(collector_id).await {
            Ok(result) => return Ok(result),
            Err(e) if attempt < 3 => {
                tracing::warn!("重试 {}/3: {}", attempt, e);
                tokio::time::sleep(Duration::from_secs(60)).await;
            }
            Err(e) => return Err(e),
        }
    }
}
```

##### 场景3：数据写入
```
问题：数据写入PostgreSQL会不会阻塞？

分析：
- 数据量：小（10-100条/次）
- 写入时间：<100ms
- 频率：低（每天几次）

结论：不需要队列
方案：直接写入即可
```

##### 场景4：未来扩展
```
问题：未来数据量大了怎么办？

分析：
- 短期（6个月）：数据量仍然小
- 中期（12个月）：可能增长到1000条/天
- 长期（18个月）：可能增长到10000条/天

结论：短期不需要，中长期再评估

触发条件：
- 单次采集 > 1000条
- 采集频率 > 每小时
- 并发采集 > 5个
```

---

### 消息队列评估结论

#### ❌ 当前不需要消息队列

##### 理由
```
1. 数据量小（10-100条/次）
2. 并发低（可串行执行）
3. 无复杂异步处理
4. 定时任务足够
5. 增加复杂度
```

##### 如果未来需要（触发条件）
```
当出现以下情况时再考虑：
- 单次采集 > 1000条
- 需要实时采集（秒级）
- 复杂的异步处理流程
- 多个消费者处理同一任务
```

##### 如果加队列（未来参考）
```toml
# 推荐方案
lapin = "2.3"  # RabbitMQ（功能完整）
# 或
redis-queue = "0.3"  # 基于Redis（简单）

# 不推荐
# Kafka（过重）
# NATS（过于简单）
```

---

## 📊 最终技术栈（更新）

### ✅ 必需组件（7个）

#### 核心基础（4个）
```
1. SeaORM        - 数据访问
2. thiserror     - 错误处理
3. tracing       - 日志系统
4. dotenvy       - 环境变量
```

#### 核心功能（3个）
```
5. Redis客户端   - 缓存 + Pub/Sub
6. 定时任务      - 自动化调度
7. 消息通知      - WebSocket + Redis Pub/Sub（零新增）
```

**总增加代码量：~410行**
- 核心4件套：~30行
- Redis：~100行
- 定时任务：~200行
- 消息通知：~150行（零新增依赖）

---

### ❌ 暂不添加（4个）

```
✗ 消息队列    - 数据量小，不需要
✗ 邮件通知    - 当前Web端通知够用
✗ API文档     - 只有自己用
✗ 监控指标    - 个人系统
```

---

## 🎯 实施计划（更新）

### 今晚/明天（2.5小时）

#### 阶段1：基础设施（1小时）
```
1. SeaORM + 错误 + 日志 + 环境变量（30分钟）
2. Redis客户端（30分钟）
```

#### 阶段2：核心功能（1小时）
```
3. 定时任务基础（30分钟）
4. 消息通知（WebSocket + Pub/Sub）（30分钟）
```

#### 阶段3：Web端（30分钟）
```
5. 定时任务管理API（15分钟）
6. 消息通知API（15分钟）
```

---

## 💡 关键决策

### 消息通知：✅ 加入（简化版）
```
方案：Redis Pub/Sub + Axum WebSocket
依赖：零新增
代码：~150行
理由：核心需求，零成本
```

### 消息队列：❌ 不加入
```
理由：
- 数据量小
- 并发低
- 定时任务够用
- 避免过度设计

何时重新评估：
- 单次采集 > 1000条
- 实时采集需求
- 复杂异步流程
```

---

## 📝 总结

### 最终方案：7个组件

**4个基础 + 3个功能**
1. SeaORM
2. thiserror  
3. tracing
4. dotenvy
5. Redis（缓存 + Pub/Sub）
6. 定时任务
7. 消息通知（零新增依赖）

**不加入**:
- ❌ 消息队列（当前不需要）
- ❌ 邮件/Telegram（Web端够用）
- ❌ 其他监控

**总代码量**: ~410行
**新增依赖**: 6个（无消息通知额外依赖）

---

**刀哥，这个方案：**
- ✅ 统一消息通知（零新增依赖）
- ✅ 不加消息队列（避免过度设计）
- ✅ 保持系统简洁
- ✅ 满足核心需求

**要不要确认这个最终方案？** 🌽✨
