# 玉米研究系统V2 - kiro.rs完全复刻对标清单

**目标**: 100%复刻kiro.rs，不是"像"，而是"完全一样"
**参考源**: /Users/apple/Progame/kiro.rs/admin-ui

---

## 🎯 对标方法论

### 1. 测量优先，不要猜测
- ✅ 读取kiro.rs源码的实际值
- ✅ 使用浏览器DevTools测量真实尺寸
- ❌ 不凭感觉调整

### 2. 像素级精确
- 每个padding、margin、font-size都要完全匹配
- 颜色值精确到HSL数值
- 动画时长和缓动曲线完全一致

### 3. 交互行为一致
- hover状态
- focus状态  
- active状态
- disabled状态
- 过渡动画

---

## 📋 待对标的细节清单

### A. 基础组件微调

#### Button
- [ ] focus-visible ring颜色和宽度
- [ ] hover时的阴影变化
- [ ] active时的transform scale
- [ ] disabled时的opacity值

#### Input
- [ ] border hover颜色过渡
- [ ] focus时ring的offset
- [ ] placeholder颜色和透明度
- [ ] file input的样式

#### Badge
- [ ] 各variant的精确颜色值
- [ ] border透明度
- [ ] padding是否对称

#### Card
- [ ] shadow的具体值
- [ ] border透明度
- [ ] hover时的阴影变化（如果有）

#### Checkbox
- [ ] checked时的背景动画
- [ ] indeterminate状态
- [ ] ring offset值

### B. 布局组件

#### Sidebar
- [ ] 折叠动画的ease-out曲线参数
- [ ] Logo区域的exact padding
- [ ] 菜单项之间的exact spacing
- [ ] 子菜单的exact缩进
- [ ] Footer的exact padding
- [ ] 滚动条样式细节

#### Header
- [ ] Badge间距
- [ ] 工具图标间距
- [ ] 分隔线的exact高度和颜色
- [ ] shadow值

#### 面包屑
- [ ] 分隔符的exact颜色和透明度
- [ ] hover时的颜色变化
- [ ] 当前项的font-weight

### C. 表格组件

#### Table Header
- [ ] 背景色exact值
- [ ] 文字颜色exact值
- [ ] padding exact值
- [ ] border颜色

#### Table Row
- [ ] hover背景色的exact透明度
- [ ] 选中背景色的exact透明度
- [ ] border颜色
- [ ] transition duration

#### Table Cell
- [ ] padding exact值
- [ ] 对齐方式
- [ ] 溢出文本处理

### D. 交互组件

#### Dialog
- [ ] overlay颜色和透明度
- [ ] content的max-width
- [ ] padding值
- [ ] 圆角大小
- [ ] 出现/消失动画

#### Dropdown Menu
- [ ] content宽度
- [ ] item高度
- [ ] item padding
- [ ] hover背景色
- [ ] 分隔线样式

#### Toast
- [ ] 位置
- [ ] 宽度
- [ ] padding
- [ ] shadow
- [ ] 动画参数

#### Tooltip
- [ ] 背景色
- [ ] padding
- [ ] 箭头大小
- [ ] 延迟时间

### E. 动画系统

#### 缓动曲线
- [ ] 确认所有cubic-bezier值
- [ ] ease-apple是否定义
- [ ] 各组件的duration

#### 关键帧动画
- [ ] card-in
- [ ] fade-in
- [ ] slide-in
- [ ] scale-in

### F. 颜色系统

#### CSS变量完整性
- [ ] 所有--theme-*变量
- [ ] 所有语义化颜色变量
- [ ] 浅色/深色模式的所有覆盖

#### 透明度使用
- [ ] border透明度
- [ ] hover背景透明度
- [ ] overlay透明度

---

## 🔍 下一步行动

1. **立即**: 逐个打开kiro.rs UI组件，复制exact值
2. **今晚**: 创建完整的CSS变量对照表
3. **明天**: 实现所有缺失的交互状态

---

**方法**: 
- 打开kiro.rs源码
- 打开我们的组件
- 逐行对比
- 发现差异立即修正
