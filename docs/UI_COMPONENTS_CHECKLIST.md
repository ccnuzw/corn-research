# 玉米研究系统V2 - UI组件对标清单

**参照标准**: kiro.rs admin-ui
**创建时间**: 2026-10-20 20:20

---

## 🎯 待对标的组件和细节

### 1. ✅ 已完成
- [x] Sidebar菜单选中状态（bg-accent + shadow）
- [x] Sidebar间距优化（py-2.5, gap-3）
- [x] 主题系统完整重写（动态色相变化）
- [x] 浅色/深色模式支持
- [x] StatCard精细化（更小字体）

---

### 2. 🔄 需要优化的字体尺寸

#### 卡片标题
- [ ] CardTitle: text-lg → **text-base** (16px → 14px)
- [ ] CardDescription: text-sm → **text-[12px]** (14px → 12px)
- [ ] StatCard标题: 已是12px ✓
- [ ] StatCard数值: 36px可能还需要调整

#### 页面标题
- [ ] 主内容区标题: 需要统一为 **text-lg** (18px)
- [ ] 面包屑: **text-[12px]**
- [ ] 子标题/描述: **text-[13px]**

---

### 3. 📦 缺失的组件

#### 基础UI组件
- [ ] Tabs（多页切换）
- [ ] Dialog/Modal
- [ ] Dropdown Menu
- [ ] Breadcrumb（面包屑）
- [ ] Input/Select/Textarea
- [ ] Checkbox/Radio/Switch
- [ ] Toast/Alert
- [ ] Progress Bar
- [ ] Skeleton Loading

#### 布局组件
- [ ] Sidebar折叠功能（collapsed state）
- [ ] 移动端响应式支持
- [ ] 主内容区滚动容器

---

### 4. 🎨 按钮样式细化
- [ ] size="sm": h-8 (当前h-9)
- [ ] size="default": h-9 (当前h-10)
- [ ] icon按钮: h-8 w-8 (当前h-10 w-10)
- [ ] 文字大小: text-[13px]

---

### 5. 📏 间距和尺寸
- [ ] 主内容区padding: p-6 → **p-5**
- [ ] 卡片padding: p-6 → **p-5**
- [ ] 卡片间距: gap-6 → **gap-4**
- [ ] 容器max-width规范

---

### 6. 🎭 其他细节
- [ ] 图表tooltip样式
- [ ] 表格样式
- [ ] 加载状态动画
- [ ] 空状态提示
- [ ] 错误状态样式

---

## 📋 下一步行动

1. **立即**: 修复所有字体大小（CardTitle、描述等）
2. **今晚**: 实现Tabs、Dialog等核心组件
3. **明天**: Sidebar折叠功能 + 移动端响应式

---

**备注**: 所有组件都要完全对标kiro.rs，不要凭感觉，要逐一比对实际代码和截图。
