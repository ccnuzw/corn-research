# 开发者文档

**版本**: v2.0.0-release  
**日期**: 2026-10-21  

## 目录

1. [环境搭建](#环境搭建)
2. [代码规范](#代码规范)
3. [开发工作流](#开发工作流)
4. [测试指南](#测试指南)
5. [调试技巧](#调试技巧)
6. [贡献指南](#贡献指南)

---

## 环境搭建

### 前置要求

- **Node.js**: 18.0.0+
- **Rust**: 1.80.0+
- **Python**: 3.11+
- **PostgreSQL**: 16+
- **Redis**: 7+
- **Git**: 2.30+

### 安装依赖

#### macOS

```bash
# Homebrew安装工具
brew install node rust python@3.11 postgresql redis git

# 验证版本
node --version  # v18+
cargo --version # 1.80+
python3 --version # 3.11+
psql --version # 16+
redis-server --version # 7+
```

#### Linux (Ubuntu/Debian)

```bash
# 安装Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 安装Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 安装Python 3.11
sudo apt-get install python3.11 python3.11-venv python3.11-dev

# 安装PostgreSQL 16
sudo apt-get install postgresql-16

# 安装Redis
sudo apt-get install redis-server
```

### 克隆项目

```bash
git clone <repository-url>
cd CornV2
```

### 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
vim .env
```

**.env 示例**:
```env
# 数据库
DATABASE_URL=postgresql://corn_user:corn_pass_2024@localhost:15432/corn_research

# Redis
REDIS_URL=redis://localhost:16380

# 后端
BACKEND_PORT=18000
RUST_LOG=debug

# 前端
NEXT_PUBLIC_API_URL=http://localhost:18000
```

### 启动数据库

```bash
# 使用Docker Compose启动
docker-compose up -d postgres redis

# 或本地启动
# PostgreSQL
brew services start postgresql@16

# Redis
brew services start redis
```

### 初始化数据库

```bash
# 运行迁移脚本
./scripts/migrate_db.sh

# 或手动执行
psql -U corn_user -d corn_research -f migrations/001_create_raw_table.sql
psql -U corn_user -d corn_research -f migrations/002_create_standard_table.sql
```

### 启动后端

```bash
cd backend-rust

# 构建
cargo build

# 运行（开发模式）
cargo run

# 运行（生产模式）
cargo run --release

# 后端运行在 http://localhost:18000
```

### 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 运行开发服务器
npm run dev

# 构建生产版本
npm run build

# 运行生产服务器
npm start

# 前端运行在 http://localhost:3080
```

### 安装Python依赖

```bash
cd collectors-python

# 创建虚拟环境
python3.11 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或
.\venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

---

## 代码规范

### Rust代码规范

遵循官方[Rust Style Guide](https://doc.rust-lang.org/1.0.0/style/)。

**关键点**:

1. **命名规范**:
   ```rust
   // 类型和Trait: PascalCase
   struct UserData { }
   trait Collector { }
   
   // 函数和变量: snake_case
   fn get_user_data() { }
   let user_name = "John";
   
   // 常量: SCREAMING_SNAKE_CASE
   const MAX_ITEMS: usize = 100;
   ```

2. **错误处理**:
   ```rust
   // 使用Result类型
   fn fetch_data() -> Result<Data, Error> {
       // ...
   }
   
   // 使用?操作符传播错误
   let data = fetch_data()?;
   
   // 避免unwrap()，使用expect()或匹配
   let value = option.expect("Value should exist");
   ```

3. **文档注释**:
   ```rust
   /// 获取用户数据
   ///
   /// # Arguments
   /// * `user_id` - 用户ID
   ///
   /// # Returns
   /// 用户数据或错误
   ///
   /// # Example
   /// ```
   /// let data = get_user_data(123)?;
   /// ```
   pub async fn get_user_data(user_id: i32) -> Result<UserData, Error> {
       // ...
   }
   ```

4. **格式化**:
   ```bash
   # 自动格式化代码
   cargo fmt
   
   # 检查代码风格
   cargo clippy
   ```

### TypeScript代码规范

遵循[Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)。

**关键点**:

1. **类型注解**:
   ```typescript
   // 明确的类型注解
   function getUserName(userId: number): string {
     return `user_${userId}`;
   }
   
   // 接口定义
   interface UserData {
     id: number;
     name: string;
     email?: string;  // 可选字段
   }
   
   // 泛型
   function fetchData<T>(url: string): Promise<T> {
     // ...
   }
   ```

2. **组件规范**:
   ```typescript
   // 使用函数组件
   export function UserCard({ user }: { user: UserData }) {
     return (
       <div className="user-card">
         <h2>{user.name}</h2>
       </div>
     );
   }
   
   // Props类型
   interface Props {
     title: string;
     onSubmit: (data: FormData) => void;
   }
   
   export function Form({ title, onSubmit }: Props) {
     // ...
   }
   ```

3. **异步处理**:
   ```typescript
   // 使用async/await
   async function fetchUser(id: number): Promise<User> {
     try {
       const response = await fetch(`/api/users/${id}`);
       return await response.json();
     } catch (error) {
       console.error('Failed to fetch user:', error);
       throw error;
     }
   }
   ```

4. **格式化**:
   ```bash
   # 使用Prettier
   npm run format
   
   # 检查代码风格
   npm run lint
   ```

### Python代码规范

遵循[PEP 8](https://www.python.org/dev/peps/pep-0008/)。

**关键点**:

1. **命名规范**:
   ```python
   # 类: PascalCase
   class DataCollector:
       pass
   
   # 函数和变量: snake_case
   def fetch_data():
       user_name = "John"
   
   # 常量: SCREAMING_SNAKE_CASE
   MAX_RETRIES = 3
   ```

2. **类型提示**:
   ```python
   from typing import List, Optional, Dict
   
   def get_users(limit: int = 10) -> List[Dict[str, any]]:
       """获取用户列表"""
       return []
   
   def find_user(user_id: int) -> Optional[Dict[str, any]]:
       """查找用户，可能返回None"""
       return None
   ```

3. **文档字符串**:
   ```python
   def fetch_data(url: str, timeout: int = 30) -> dict:
       """
       从URL获取数据
       
       Args:
           url: 目标URL
           timeout: 超时时间（秒）
       
       Returns:
           解析后的JSON数据
       
       Raises:
           requests.RequestException: 请求失败
       """
       pass
   ```

4. **格式化**:
   ```bash
   # 使用black
   black collectors-python/
   
   # 使用pylint检查
   pylint collectors-python/
   ```

### Git提交规范

遵循[Conventional Commits](https://www.conventionalcommits.org/)。

**格式**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型**:
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具相关

**示例**:
```bash
git commit -m "feat(collectors): 添加新浪财经采集器"
git commit -m "fix(api): 修复数据查询分页bug"
git commit -m "docs(readme): 更新安装说明"
git commit -m "test(e2e): 添加采集器端到端测试"
```

---

## 开发工作流

### 分支策略

```
main (生产)
  ↓
develop (开发)
  ↓
feature/xxx (功能分支)
hotfix/xxx (紧急修复)
```

### 开发新功能

```bash
# 1. 从develop创建功能分支
git checkout develop
git pull origin develop
git checkout -b feature/new-collector

# 2. 开发功能
# ... 编写代码 ...

# 3. 提交代码
git add .
git commit -m "feat(collectors): 添加DCE采集器"

# 4. 推送到远程
git push origin feature/new-collector

# 5. 创建Pull Request
gh pr create --base develop --head feature/new-collector

# 6. 代码审查通过后合并
gh pr merge
```

### 修复Bug

```bash
# 1. 从相应分支创建修复分支
git checkout develop
git checkout -b fix/query-pagination

# 2. 修复Bug并测试
# ... 修复代码 ...

# 3. 提交
git commit -m "fix(api): 修复数据查询分页越界问题"

# 4. 推送并创建PR
git push origin fix/query-pagination
gh pr create
```

### 紧急修复（Hotfix）

```bash
# 1. 从main创建hotfix分支
git checkout main
git checkout -b hotfix/critical-bug

# 2. 快速修复
# ... 修复代码 ...

# 3. 提交并推送
git commit -m "fix: 修复数据库连接泄漏问题"
git push origin hotfix/critical-bug

# 4. 合并到main和develop
git checkout main
git merge hotfix/critical-bug
git checkout develop
git merge hotfix/critical-bug
```

---

## 测试指南

### 单元测试

#### Rust单元测试

```rust
#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_quality_score() {
        let score = calculate_quality_score("官方", true, true);
        assert_eq!(score, 100.0);
    }
    
    #[tokio::test]
    async fn test_fetch_data() {
        let result = fetch_data("https://example.com").await;
        assert!(result.is_ok());
    }
}

// 运行测试
// cargo test
```

#### TypeScript单元测试

```typescript
// __tests__/utils.test.ts
import { formatDate } from '../lib/utils';

describe('formatDate', () => {
  it('should format date correctly', () => {
    const date = new Date('2026-10-21');
    expect(formatDate(date)).toBe('2026-10-21');
  });
});

// 运行测试
// npm test
```

#### Python单元测试

```python
# tests/test_collector.py
import unittest
from collectors.boyar_production import BoyarProductionCollector

class TestBoyarCollector(unittest.TestCase):
    def test_parse_data(self):
        collector = BoyarProductionCollector()
        result = collector.parse('<html>...</html>')
        self.assertIsNotNone(result)
    
    def test_rate_limit(self):
        # 测试限速机制
        pass

# 运行测试
# python -m unittest discover tests
```

### 集成测试

```bash
# 运行所有集成测试
cd tests/integration
python test_api.py
```

### 端到端测试

```bash
# 确保所有服务运行
docker-compose up -d

# 运行E2E测试
cd tests/e2e
python test_collectors.py
python test_data_pipeline.py
python test_frontend.py
```

### 性能测试

```bash
# 运行性能基准测试
cd tests/performance
python benchmark.py
```

### 测试覆盖率

```bash
# Rust覆盖率
cargo tarpaulin --out Html

# TypeScript覆盖率
npm run test:coverage

# Python覆盖率
coverage run -m unittest discover
coverage report
coverage html
```

---

## 调试技巧

### Rust调试

#### 使用日志

```rust
use tracing::{info, debug, error};

#[tokio::main]
async fn main() {
    // 初始化日志
    tracing_subscriber::fmt::init();
    
    info!("Starting application");
    debug!("Debug information: {:?}", data);
    error!("Error occurred: {}", err);
}

// 设置日志级别
// RUST_LOG=debug cargo run
```

#### 使用调试器

```bash
# 使用rust-lldb
rust-lldb target/debug/corn-backend

# 设置断点
(lldb) b main.rs:42
(lldb) r

# 使用VS Code调试
# 配置 .vscode/launch.json
```

### TypeScript调试

#### 浏览器调试

```typescript
// 使用console
console.log('Data:', data);
console.error('Error:', error);
console.table(users);

// 使用debugger
function processData(data: any) {
  debugger;  // 浏览器会在此处暂停
  // ...
}
```

#### VS Code调试

```json
// .vscode/launch.json
{
  "type": "node",
  "request": "launch",
  "name": "Next.js: debug",
  "runtimeExecutable": "npm",
  "runtimeArgs": ["run", "dev"],
  "port": 9229
}
```

### Python调试

```python
# 使用print调试
print(f"Debug: {variable}")

# 使用pdb
import pdb
pdb.set_trace()  # 在此处设置断点

# 使用logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("Debug message")
```

### 数据库调试

```sql
-- 查看慢查询
SELECT * FROM pg_stat_statements 
WHERE total_time > 1000 
ORDER BY total_time DESC;

-- 分析查询计划
EXPLAIN ANALYZE 
SELECT * FROM market_facts_standard 
WHERE business_date > '2026-10-01';

-- 查看锁
SELECT * FROM pg_locks;
```

### Redis调试

```bash
# 连接Redis
redis-cli -p 16380

# 查看所有键
KEYS *

# 查看键值
GET cache:api:collectors

# 监控命令
MONITOR

# 查看信息
INFO
```

---

## 贡献指南

### 代码审查清单

提交PR前检查：

- [ ] 代码符合规范（运行linter）
- [ ] 所有测试通过
- [ ] 添加了必要的测试
- [ ] 更新了文档
- [ ] 提交信息符合规范
- [ ] 无合并冲突
- [ ] 代码有适当的注释
- [ ] 错误处理完善
- [ ] 性能影响可接受

### PR模板

```markdown
## 变更说明
<!-- 描述本次变更的内容 -->

## 变更类型
- [ ] 新功能
- [ ] Bug修复
- [ ] 文档更新
- [ ] 代码重构
- [ ] 性能优化
- [ ] 其他

## 测试
<!-- 描述如何测试本次变更 -->

## 截图（如适用）
<!-- 添加截图 -->

## 检查清单
- [ ] 代码通过linter检查
- [ ] 所有测试通过
- [ ] 添加了必要的测试
- [ ] 更新了文档
```

### 发布流程

```bash
# 1. 更新版本号
# 修改 Cargo.toml, package.json 中的版本号

# 2. 更新CHANGELOG
# 记录本次发布的变更

# 3. 创建tag
git tag -a v2.0.0 -m "Release v2.0.0"
git push origin v2.0.0

# 4. 构建发布包
cargo build --release
npm run build

# 5. 创建GitHub Release
gh release create v2.0.0 --notes "Release notes"
```

---

## 常用命令

### 开发命令

```bash
# Rust
cargo build              # 构建
cargo run                # 运行
cargo test               # 测试
cargo fmt                # 格式化
cargo clippy             # 检查

# Node.js
npm install              # 安装依赖
npm run dev              # 开发模式
npm run build            # 构建
npm test                 # 测试
npm run lint             # 检查

# Python
pip install -r requirements.txt  # 安装依赖
python -m unittest discover      # 测试
black .                          # 格式化
pylint .                         # 检查

# Docker
docker-compose up -d     # 启动服务
docker-compose down      # 停止服务
docker-compose logs -f   # 查看日志
docker-compose ps        # 查看状态
```

### 数据库命令

```bash
# 连接数据库
psql -U corn_user -d corn_research -h localhost -p 15432

# 备份
pg_dump -U corn_user corn_research > backup.sql

# 恢复
psql -U corn_user -d corn_research < backup.sql

# 迁移
./scripts/migrate_db.sh
```

---

## 参考资源

### 官方文档
- [Rust Book](https://doc.rust-lang.org/book/)
- [Axum Guide](https://docs.rs/axum/)
- [Next.js Docs](https://nextjs.org/docs)
- [PostgreSQL Manual](https://www.postgresql.org/docs/)

### 工具
- [cargo-watch](https://github.com/watchexec/cargo-watch) - 自动重新编译
- [cargo-edit](https://github.com/killercup/cargo-edit) - 管理依赖
- [Postman](https://www.postman.com/) - API测试
- [pgAdmin](https://www.pgadmin.org/) - PostgreSQL管理

---

**维护者**: 玉米研究团队  
**最后更新**: 2026-10-21
