# 密码轮换指南

## 泄露的密码清单

以下密码已在Git历史中泄露，需要立即更换：

1. **PostgreSQL密码**: `corn_password_2026`
   - 泄露位置: docker-compose.yml, 测试代码, 文档
   - 风险: 数据库完全访问

2. **测试密码**: `corn_pass`
   - 泄露位置: test_mock_quality.py
   - 风险: 测试环境可能使用真实数据

3. **文档示例密码**: `corn_pass_2024`
   - 泄露位置: docs/DEVELOPER.md
   - 风险: 开发者可能复用

## 轮换步骤

### 1. 生成新密码 (立即执行)

```bash
# 生成强密码
export NEW_POSTGRES_PASSWORD=$(openssl rand -base64 32)
export NEW_REDIS_PASSWORD=$(openssl rand -base64 32)

# 保存到安全位置
echo "POSTGRES_PASSWORD=$NEW_POSTGRES_PASSWORD" >> .env.production
echo "REDIS_PASSWORD=$NEW_REDIS_PASSWORD" >> .env.production
chmod 600 .env.production
```

### 2. 更新数据库密码

```bash
# 连接到PostgreSQL
docker exec -it corn_postgres psql -U corn_user -d corn_research

# 修改密码
ALTER USER corn_user WITH PASSWORD 'your_new_password_here';
\q

# 更新环境变量
export POSTGRES_PASSWORD='your_new_password_here'
export DATABASE_URL="postgresql://corn_user:${POSTGRES_PASSWORD}@localhost:15432/corn_research"
```

### 3. 重启服务

```bash
# 使用新密码重启
docker-compose down
docker-compose up -d

# 验证连接
docker-compose logs backend | grep "Database connected"
```

### 4. 更新测试代码

```python
# test_mock_quality.py
# 替换硬编码密码为环境变量
import os
conn = await asyncpg.connect(
    host='localhost',
    port=5433,
    user='corn_user',
    password=os.getenv('POSTGRES_PASSWORD'),  # ✅ 从环境变量读取
    database='corn_research'
)
```

### 5. 更新文档

在所有文档中替换真实密码为占位符：
- ❌ `corn_password_2026`
- ✅ `your_secure_password_here`

### 6. 清理Git历史 (可选但推荐)

```bash
# ⚠️ 危险操作，请先备份仓库

# 从历史中移除敏感文件
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch docker-compose.yml .env" \
  --prune-empty --tag-name-filter cat -- --all

# 或使用 BFG Repo-Cleaner (更安全)
brew install bfg
bfg --replace-text passwords.txt  # 包含所有旧密码的文件

# 强制推送 (仅当确认安全)
git push origin --force --all
git push origin --force --tags
```

## 验证清单

- [ ] 生成新的强密码 (32字符以上)
- [ ] 更新PostgreSQL密码
- [ ] 更新Redis密码
- [ ] 重启所有服务
- [ ] 验证连接成功
- [ ] 更新测试代码
- [ ] 更新文档示例
- [ ] 考虑清理Git历史
- [ ] 通知团队成员更新本地配置

## 定期轮换建议

- 生产环境: 每90天
- 开发环境: 每180天
- 泄露后: 立即

## 密码策略

- 长度: ≥32字符
- 字符集: 大小写字母 + 数字 + 特殊字符
- 禁止: 字典词汇、常见模式、重复字符
- 存储: 环境变量或密钥管理系统
- 传输: 仅通过加密通道

## 紧急联系

如发现密码已被滥用:
1. 立即轮换所有密码
2. 审计数据库访问日志
3. 检查数据完整性
4. 通知安全团队
