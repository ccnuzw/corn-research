# 🎨 玉米研究系统V2 - UI/UX设计规范

**基于claude-opus-5-5设计标准**  
**日期**: 2026-10-20

---

## 📐 设计原则

参照claude-opus-5-5的设计语言，建立玉米研究系统的UI/UX标准：

### 核心理念
1. **专业技术感** - 深色主题 + 青绿色强调
2. **信息密度高** - 充分利用空间展示数据
3. **扁平化+微阴影** - 避免过度装饰
4. **语义化配色** - 图表颜色清晰区分
5. **一致性强** - 组件风格统一

---

## 🎨 配色系统

### 5个主题色板（参考claude-opus-5-5）

#### 1. 清透青（默认主题）
```css
--theme-hue: 174;
--theme-chroma: 24%;
--theme-primary-light: hsl(174, 72%, 29%);
--theme-primary-dark: hsl(172, 62%, 57%);
--accent-color: #7ce3cb; /* 薄荷青 */
```

#### 2. 石墨灰
```css
--theme-hue: 220;
--theme-chroma: 12%;
--theme-primary-light: hsl(220, 15%, 25%);
--theme-primary-dark: hsl(220, 20%, 60%);
--accent-color: #94a3b8; /* 银灰色 */
```

#### 3. 海洋蓝
```css
--theme-hue: 210;
--theme-chroma: 40%;
--theme-primary-light: hsl(210, 80%, 35%);
--theme-primary-dark: hsl(210, 70%, 60%);
--accent-color: #3b82f6; /* 蓝色 */
```

#### 4. 松林绿
```css
--theme-hue: 142;
--theme-chroma: 35%;
--theme-primary-light: hsl(142, 70%, 30%);
--theme-primary-dark: hsl(142, 60%, 55%);
--accent-color: #10b981; /* 翠绿色 */
```

#### 5. 琥珀金
```css
--theme-hue: 38;
--theme-chroma: 45%;
--theme-primary-light: hsl(38, 85%, 45%);
--theme-primary-dark: hsl(38, 75%, 60%);
--accent-color: #f59e0b; /* 琥珀色 */
```

### 基础色彩变量（深色模式）
```css
:root[data-theme="system"].dark {
  /* 背景层次 */
  --background: hsl(var(--theme-hue) var(--theme-chroma) 6%);    /* 最深背景 #0a0e12 */
  --surface-1: hsl(var(--theme-hue) var(--theme-chroma) 10%);   /* 卡片背景 #1a2028 */
  --surface-2: hsl(var(--theme-hue) var(--theme-chroma) 14%);   /* 悬浮层 */
  
  /* 文字层次 */
  --foreground: hsl(220, 12%, 92%);      /* 主文字 #e6edf3 */
  --foreground-muted: hsl(220, 8%, 55%); /* 次要文字 #8b949e */
  --foreground-dimmed: hsl(220, 8%, 43%);/* 说明文字 #6e7681 */
  
  /* 边框 */
  --border: hsl(var(--theme-hue) 12% 18%); /* #30363d */
  --border-muted: hsl(var(--theme-hue) 8% 12%);
  
  /* 交互色 */
  --primary: var(--theme-primary-dark);
  --primary-hover: hsl(var(--theme-hue) calc(var(--theme-chroma) + 5%) 65%);
  --accent: var(--accent-color);
}
```

### 图表配色（语义化）
```css
--chart-blue: #3b82f6;    /* 输入/请求 */
--chart-green: #10b981;   /* 输出/成功 */
--chart-yellow: #f59e0b;  /* 警告/缓存 */
--chart-cyan: #06b6d4;    /* 信息/读取 */
--chart-purple: #a855f7;  /* 特殊/中毒 */
--chart-red: #ef4444;     /* 错误/失败 */
```

---

## 📏 布局系统

### 主布局结构（参考claude-opus-5-5）

```
┌──────────────────────────────────────────────────┐
│  顶部导航栏（60px）                              │
│  Logo + 页面标题 + 状态指示 + 工具栏             │
├───────┬──────────────────────────────────────────┤
│       │  主内容区                                │
│  左   │  ┌────────────────────────────────┐     │
│  侧   │  │  面包屑 + 时间范围              │     │
│  导   │  ├────────────────────────────────┤     │
│  航   │  │  统计卡片（4列）                │     │
│  栏   │  ├────────────────────────────────┤     │
│       │  │  筛选条件栏                     │     │
│200px │  ├────────────────────────────────┤     │
│       │  │  主图表区域                     │     │
│       │  ├────────────────────────────────┤     │
│       │  │  数据表格                       │     │
│       │  └────────────────────────────────┘     │
└───────┴──────────────────────────────────────────┘
```

### 间距系统
```css
--spacing-xs: 4px;
--spacing-sm: 8px;
--spacing-md: 16px;
--spacing-lg: 24px;
--spacing-xl: 32px;
--spacing-2xl: 48px;
```

### 圆角系统
```css
--radius-sm: 4px;   /* 标签 */
--radius-md: 6px;   /* 按钮 */
--radius-lg: 8px;   /* 卡片 */
--radius-xl: 12px;  /* 对话框 */
```

---

## 🧩 组件设计

### 1. 导航栏（Sidebar）

```tsx
// 设计规格
- 宽度: 200px
- 背景: var(--surface-1)
- 项目高度: 40px
- 项目圆角: 6px
- 选中背景: var(--primary) with 15% opacity
- 图标尺寸: 20px
- 字体大小: 14px

// 菜单结构
- 仪表概览（Dashboard）
- 采集器管理（Collectors）
- 数据监控（Data Monitor）
- 数据质量（Data Quality）
- 系统设置（Settings）
  - 数据源配置
  - 主题设置
  - 系统日志
```

### 2. 统计卡片（Stat Card）

```tsx
// 设计规格
<Card className="stat-card">
  <CardIcon />              {/* 左上角图标 */}
  <CardTitle />             {/* 标题 + 时间范围 */}
  <CardValue />             {/* 大号数字 */}
  <CardTrend />             {/* 趋势指示 */}
</Card>

// CSS
.stat-card {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  min-height: 140px;
}

.stat-card-value {
  font-size: 48px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace; /* 等宽字体 */
  line-height: 1;
}
```

### 3. 主题选择器（Theme Picker）

```tsx
// 参考claude-opus-5-5的设计
<ThemePicker>
  {/* 主题色板预览 */}
  <ThemeGrid>
    {themes.map(theme => (
      <ThemeCard key={theme.id} selected={current === theme.id}>
        <ThemePreview colors={theme.colors} />
        <ThemeName>{theme.name}</ThemeName>
        {selected && <CheckIcon />}
      </ThemeCard>
    ))}
  </ThemeGrid>
  
  {/* 明暗模式切换 */}
  <ModeSelector>
    <ModeButton icon={<Monitor />}>跟随系统</ModeButton>
    <ModeButton icon={<Sun />}>浅色</ModeButton>
    <ModeButton icon={<Moon />}>深色</ModeButton>
  </ModeSelector>
</ThemePicker>
```

### 4. 数据图表（Charts）

```tsx
// 使用recharts，参考claude-opus-5-5样式
<AreaChart>
  {/* 配置 */}
  <CartesianGrid 
    stroke="var(--border-muted)" 
    strokeDasharray="3 3" 
  />
  <YAxis 
    stroke="var(--foreground-dimmed)"
    tick={{ fontSize: 12 }}
  />
  <Tooltip 
    contentStyle={{
      background: 'var(--surface-2)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-md)'
    }}
  />
  <Area 
    type="monotone" 
    dataKey="value"
    stroke="var(--chart-blue)"
    fill="var(--chart-blue)"
    fillOpacity={0.2}
  />
</AreaChart>
```

---

## 🔤 字体系统

### 字体家族
```css
--font-sans: 'Inter', 'PingFang SC', -apple-system, system-ui, sans-serif;
--font-mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace;
--font-serif: 'Noto Serif SC', serif;
```

### 字体大小
```css
--text-xs: 12px;   /* 说明文字 */
--text-sm: 13px;   /* 次要文字 */
--text-base: 14px; /* 正文 */
--text-lg: 16px;   /* 标题 */
--text-xl: 18px;   /* 大标题 */
--text-2xl: 24px;  /* 页面标题 */
--text-3xl: 36px;  /* 统计数字 */
```

### 字重
```css
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

---

## 🎭 动画效果

### 过渡动画
```css
/* 参考claude-opus-5-5的Apple缓动曲线 */
--transition-fast: 150ms cubic-bezier(0.32, 0.72, 0, 1);
--transition-base: 200ms cubic-bezier(0.32, 0.72, 0, 1);
--transition-slow: 300ms cubic-bezier(0.32, 0.72, 0, 1);

/* 卡片入场动画 */
@keyframes card-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.card-in {
  animation: card-in 320ms cubic-bezier(0.32, 0.72, 0, 1) both;
}
```

---

## 📱 响应式设计

### 断点
```css
--breakpoint-sm: 640px;
--breakpoint-md: 768px;
--breakpoint-lg: 1024px;
--breakpoint-xl: 1280px;
--breakpoint-2xl: 1536px;
```

### 布局适配
```css
/* 小屏幕：垂直堆叠 */
@media (max-width: 768px) {
  .sidebar { display: none; }
  .stat-grid { grid-template-columns: 1fr; }
}

/* 中屏幕：2列 */
@media (min-width: 768px) and (max-width: 1024px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
}

/* 大屏幕：4列 */
@media (min-width: 1024px) {
  .stat-grid { grid-template-columns: repeat(4, 1fr); }
}
```

---

## ✅ 实施计划

### Phase 1: 基础搭建（1-2天）
1. ✅ 提取claude-opus-5-5主题系统
2. ⏳ 创建CSS变量体系
3. ⏳ 搭建布局框架
4. ⏳ 实现主题切换

### Phase 2: 组件实现（2-3天）
1. ⏳ 导航栏组件
2. ⏳ 统计卡片组件
3. ⏳ 图表组件
4. ⏳ 表格组件

### Phase 3: 页面开发（3-4天）
1. ⏳ Dashboard页面
2. ⏳ 采集器管理页面
3. ⏳ 数据监控页面
4. ⏳ 设置页面

---

**刀哥，这个设计规范完全参考了claude-opus-5-5的标准！现在开始重新实现UI？** 🎨✨
