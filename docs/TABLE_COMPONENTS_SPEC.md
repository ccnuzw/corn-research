# 玉米研究系统V2 - 表格与面包屑组件对标清单

**基于截图分析** - 2026-10-20 20:25

---

## 📊 表格组件关键细节

### 1. 表头 (Table Header)
- [ ] 背景色: 略深于主背景
- [ ] 字体大小: **text-[12px]**
- [ ] 字体颜色: text-muted-foreground
- [ ] 字体粗细: font-medium (500)
- [ ] 高度: h-11 (44px)
- [ ] 内边距: px-4

### 2. 表格行 (Table Row)
- [ ] 高度: **h-14** (56px) - 比默认更高
- [ ] 底部边框: border-b border-border
- [ ] 悬停: hover:bg-accent/50
- [ ] 选中背景: **bg-accent/20** (深色半透明)

### 3. 单元格内容
- [ ] 主文字: text-[13px] font-normal
- [ ] 辅助文字: text-[12px] text-muted-foreground
- [ ] 等宽字体KEY: font-mono text-[13px]
- [ ] 内边距: px-4 py-3

### 4. 状态标签 (Badge)
- [ ] 启用: bg-green-500/10 text-green-500
- [ ] 禁用: bg-gray-500/10 text-gray-500
- [ ] 圆角: rounded-full (完全圆角)
- [ ] 内边距: px-3 py-1
- [ ] 字体: text-[12px]

### 5. 操作图标
- [ ] 尺寸: w-4 h-4 (16px)
- [ ] 间距: gap-3
- [ ] 颜色: text-muted-foreground
- [ ] 悬停: hover:text-foreground

---

## 🍞 面包屑 (Breadcrumb)

### 样式规范
- [ ] 字体大小: **text-[13px]**
- [ ] 颜色: text-muted-foreground
- [ ] 当前页: text-foreground font-medium
- [ ] 分隔符: `/` 或 `>`, text-muted-foreground/50
- [ ] 图标: w-4 h-4, 主题色
- [ ] 间距: gap-2

### 结构
```tsx
[图标] 控制台 / 客户端 Key
```

---

## 🎯 悬浮工具栏 (Floating Toolbar)

### 位置与样式
- [ ] 位置: fixed bottom-6 left-1/2 -translate-x-1/2
- [ ] 背景: bg-card border border-border/60
- [ ] 阴影: shadow-2xl
- [ ] 圆角: rounded-xl (12px)
- [ ] 内边距: px-4 py-2.5
- [ ] z-index: z-50

### 内部组件
1. **选中计数**
   - [ ] bg-accent/20 text-accent-foreground
   - [ ] px-2.5 py-1 rounded-md
   - [ ] text-[12px] font-medium

2. **分隔线**
   - [ ] w-px h-5 bg-border

3. **批量按钮**
   - [ ] variant="ghost" size="sm"
   - [ ] gap-1.5
   - [ ] text-[13px]

4. **删除按钮**
   - [ ] variant="destructive" size="sm"
   - [ ] bg-red-500/90 hover:bg-red-500

---

## ☑️ 复选框 (Checkbox)

### 样式
- [ ] 尺寸: w-4 h-4
- [ ] 边框: border-2 border-primary
- [ ] 圆角: rounded-sm (2px)
- [ ] 选中背景: bg-primary
- [ ] 勾选图标: text-primary-foreground
- [ ] 过渡: transition-all duration-200

---

## 🔢 字体尺寸总结

| 元素 | 尺寸 | 用途 |
|------|------|------|
| text-[11px] | 11px | Badge、Footer |
| text-[12px] | 12px | 表头、描述、标签 |
| text-[13px] | 13px | 表格内容、按钮、面包屑 |
| text-base | 14px | Card标题、菜单 |
| text-base | 16px | 页面标题 |

---

## 📏 间距规范

| 类型 | 值 | 用途 |
|------|-----|------|
| gap-1 | 4px | 紧密元素 |
| gap-2 | 8px | 标签内图标 |
| gap-3 | 12px | 按钮组、操作图标 |
| gap-4 | 16px | 卡片网格 |
| px-3 | 12px | 按钮小内边距 |
| px-4 | 16px | 按钮、单元格 |
| px-5 | 20px | 卡片、主内容 |
| py-2.5 | 10px | 工具栏 |
| py-3 | 12px | 单元格 |

---

## 🎨 颜色语义

| 用途 | 颜色 |
|------|------|
| 主题色 | hsl(var(--primary)) |
| 成功/启用 | text-green-500, bg-green-500/10 |
| 危险/删除 | text-red-500, bg-red-500/90 |
| 警告/电源 | text-yellow-500 |
| 选中背景 | bg-accent/20 |
| 悬停背景 | bg-accent/50 |

---

**下一步**: 实现 Table、Breadcrumb、Checkbox 和 Floating Toolbar 组件
