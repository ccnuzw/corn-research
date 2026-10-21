# 玉米研究系统V2 - kiro.rs精确对标完成清单

**完成时间**: 2026-10-20 20:50
**对标方法**: 逐行对比源码，提取exact值

---

## ✅ 已精确对标的组件

### Button
- ✅ 基础类: `gap-1.5` (was 2), `text-sm` (was text-[13px])
- ✅ 过渡: `transition-colors transition-transform duration-100 ease-out`
- ✅ focus: `focus-visible:ring-1` (was ring-2), 无ring-offset
- ✅ disabled: `opacity-40` (was 50)
- ✅ active: `active:scale-[0.96]` (新增点击缩放)
- ✅ default size: `h-8 px-3.5 py-1.5 text-xs`
- ✅ sm size: `h-7 px-2.5 text-[12px]`
- ✅ lg size: `h-9 px-4 text-sm`
- ✅ icon size: `h-8 w-8 rounded-md`
- ✅ default variant: `shadow-xs`
- ✅ outline variant: `border-input/70`, `hover:border-primary/40`
- ✅ ghost variant: `text-muted-foreground`
- ✅ link variant: `rounded-none active:scale-100`

### Badge
- ✅ focus: `focus:ring-1` (was ring-2), 无ring-offset
- ✅ destructive: `border-destructive/30 bg-destructive/10` (半透明)
- ✅ outline: `border-border bg-transparent text-foreground/85`
- ✅ success: `border-primary/20 bg-primary/10 text-primary`
- ✅ error: `border-destructive/30 bg-destructive/10`

### Input
- ✅ 字体: `text-xs` (was text-[13px])
- ✅ 过渡: `duration-100 ease-out`
- ✅ file样式: `file:text-foreground`

### Card
- ✅ padding: `p-5` (20px)
- ✅ title: `text-base leading-tight`
- ✅ border: `border-border/60`
- ✅ shadow: `shadow-[var(--surface-shadow)]`

### Checkbox
- ✅ 尺寸: `h-4 w-4`
- ✅ 边框: `border-2 border-primary`
- ✅ 圆角: `rounded-sm`

---

## 📏 精确的尺寸规范

| 组件 | 属性 | kiro.rs值 | 我们的值 | 状态 |
|------|------|-----------|----------|------|
| Button default | height | 32px (h-8) | 32px | ✅ |
| Button default | font | 12px (text-xs) | 12px | ✅ |
| Button sm | height | 28px (h-7) | 28px | ✅ |
| Button lg | height | 36px (h-9) | 36px | ✅ |
| Input | height | 32px (h-8) | 32px | ✅ |
| Input | font | 12px (text-xs) | 12px | ✅ |
| Badge | font | 11px | 11px | ✅ |
| Card padding | all | 20px (p-5) | 20px | ✅ |
| Card title | font | 14px (text-base) | 14px | ✅ |

---

## 🎨 精确的交互效果

### Button
- ✅ hover: `bg-primary/90` (90%透明度)
- ✅ active: 缩放到96% (`scale-[0.96]`)
- ✅ transition: 100ms ease-out
- ✅ focus ring: 1px宽度

### Input
- ✅ hover: border颜色变化
- ✅ focus: `ring-1` + `border-primary`
- ✅ transition: 100ms ease-out

---

## 🎯 动画系统

### 缓动曲线
- ✅ ease-out: 标准缓动
- ✅ duration-100: 100ms
- ✅ duration-200: 200ms (sidebar折叠)
- ✅ cubic-bezier(0.32, 0.72, 0, 1): Apple缓动（用于卡片动画）

---

## 🚀 下一步精确对标

### 待完善组件
- [ ] Dialog
- [ ] Dropdown Menu
- [ ] Select
- [ ] Tooltip
- [ ] Toast
- [ ] Tabs
- [ ] Progress

### 待完善交互
- [ ] 表格hover效果精确透明度
- [ ] 悬浮工具栏shadow精确值
- [ ] 面包屑hover颜色
- [ ] Sidebar折叠动画ease-out参数

---

**方法论验证**:
✅ 逐行对比源码
✅ 提取exact className值
✅ 不凭感觉，只用测量

**刀哥，现在刷新浏览器，所有按钮、输入框、标签的尺寸、字体、动画都完全对标kiro.rs了！** 🎯
