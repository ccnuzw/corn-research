# 🔍 启动前检查清单

**日期**: 2026-10-20

---

## ✅ 必需检查项

### 1. 目录结构
- [ ] `/Users/apple/CornV2/backend-rust/` - Rust后端
- [ ] `/Users/apple/CornV2/frontend/` - Next.js前端
- [ ] `/Users/apple/CornV2/collectors-python/` - Python采集器
- [ ] `/Users/apple/CornV2/.venv/` - Python虚拟环境

### 2. Rust后端
- [ ] `backend-rust/Cargo.toml` - 依赖配置
- [ ] `backend-rust/src/main.rs` - 主入口
- [ ] `backend-rust/src/handlers.rs` - API处理器
- [ ] `backend-rust/src/python_bridge.rs` - Python桥接
- [ ] `cargo check` 编译通过

### 3. Python采集器
- [ ] `collectors-python/collectors/boyar.py` - 博亚和讯
- [ ] `collectors-python/collectors/sina.py` - 新浪财经
- [ ] Python依赖已安装（requests, beautifulsoup4, lxml）
- [ ] BoyarCollector可正常导入

### 4. Next.js前端
- [ ] `frontend/package.json` - 依赖配置
- [ ] `frontend/app/page.tsx` - 主页
- [ ] `frontend/lib/api.ts` - API客户端
- [ ] `frontend/.env.local` - 环境变量
- [ ] node_modules已安装

---

## 🧪 测试步骤

### Step 1: Python环境
```bash
cd /Users/apple/CornV2
source .venv/bin/activate
python -c "import requests, bs4; print('OK')"
python -c "from collectors.boyar import BoyarCollector; print('OK')"
```

### Step 2: Rust编译
```bash
cd /Users/apple/CornV2/backend-rust
cargo check
# 应该看到: Finished
```

### Step 3: 前端依赖
```bash
cd /Users/apple/CornV2/frontend
test -f package.json && echo "OK"
ls app/ lib/ components/
```

---

## ⚠️ 常见问题

### 问题1: Rust编译失败
**原因**: 依赖版本冲突  
**解决**: `cargo clean && cargo check`

### 问题2: Python导入失败
**原因**: 依赖未安装  
**解决**: `pip install requests beautifulsoup4 lxml`

### 问题3: 前端无法启动
**原因**: node_modules缺失  
**解决**: `npm install`

---

## 📋 检查结果

运行以下命令获取完整报告：
```bash
cd /Users/apple/CornV2
./scripts/pre_launch_check.sh
```
