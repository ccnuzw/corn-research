# 主题系统设计

**参考**: Kiro.rs 主题切换功能

## 设计原则

- 🎨 预配置主题套装（开箱即用）
- 🔄 一键切换，实时生效
- 💾 用户偏好持久化
- 🌓 支持自动切换（跟随系统）
- 🎭 可扩展自定义主题

## 主题列表

### 1. 科技深蓝（默认）

**适用场景**: 日常使用，护眼  
**风格**: 专业、沉稳、科技感

```css
:root[data-theme="tech-blue"] {
  /* 背景 */
  --background: #0a0e27;
  --surface: #161b33;
  --surface-hover: #1e2441;
  
  /* 主色调 */
  --primary: #667eea;
  --primary-hover: #7c8ff0;
  --secondary: #764ba2;
  --accent: #f093fb;
  
  /* 功能色 */
  --success: #4ade80;
  --warning: #fbbf24;
  --error: #ef4444;
  --info: #60a5fa;
  
  /* 文字 */
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --text-tertiary: #64748b;
  
  /* 边框 */
  --border: #1e293b;
  --border-hover: #334155;
  
  /* 渐变 */
  --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  --gradient-accent: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}
```

### 2. 财经暗夜

**适用场景**: 盯盘、专注分析  
**风格**: 类Bloomberg Terminal

```css
:root[data-theme="finance-dark"] {
  --background: #000000;
  --surface: #0d0d0d;
  --surface-hover: #1a1a1a;
  
  --primary: #00d4ff;
  --primary-hover: #1ee0ff;
  --secondary: #ff9500;
  --accent: #ffd60a;
  
  --success: #32d74b;
  --warning: #ff9f0a;
  --error: #ff453a;
  --info: #00d4ff;
  
  --text-primary: #ffffff;
  --text-secondary: #98989d;
  --text-tertiary: #636366;
  
  --border: #1c1c1e;
  --border-hover: #2c2c2e;
  
  --gradient-primary: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%);
  --gradient-accent: linear-gradient(135deg, #ff9500 0%, #ffd60a 100%);
}
```

### 3. 极简亮色

**适用场景**: 白天办公、演示  
**风格**: 清爽、简约

```css
:root[data-theme="minimal-light"] {
  --background: #ffffff;
  --surface: #f8fafc;
  --surface-hover: #f1f5f9;
  
  --primary: #3b82f6;
  --primary-hover: #2563eb;
  --secondary: #8b5cf6;
  --accent: #ec4899;
  
  --success: #10b981;
  --warning: #f59e0b;
  --error: #ef4444;
  --info: #3b82f6;
  
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-tertiary: #94a3b8;
  
  --border: #e2e8f0;
  --border-hover: #cbd5e1;
  
  --gradient-primary: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  --gradient-accent: linear-gradient(135deg, #ec4899 0%, #f43f5e 100%);
}
```

### 4. 暗夜绿境

**适用场景**: 夜间使用、护眼  
**风格**: 温暖、护眼

```css
:root[data-theme="dark-green"] {
  --background: #0d1117;
  --surface: #161b22;
  --surface-hover: #21262d;
  
  --primary: #3fb950;
  --primary-hover: #56d364;
  --secondary: #2ea043;
  --accent: #7ee787;
  
  --success: #3fb950;
  --warning: #d29922;
  --error: #f85149;
  --info: #58a6ff;
  
  --text-primary: #c9d1d9;
  --text-secondary: #8b949e;
  --text-tertiary: #6e7681;
  
  --border: #30363d;
  --border-hover: #484f58;
  
  --gradient-primary: linear-gradient(135deg, #3fb950 0%, #2ea043 100%);
  --gradient-accent: linear-gradient(135deg, #7ee787 0%, #3fb950 100%);
}
```

### 5. 紫罗兰梦

**适用场景**: 个性化、创意工作  
**风格**: 优雅、现代

```css
:root[data-theme="violet-dream"] {
  --background: #0f0a1e;
  --surface: #1a1229;
  --surface-hover: #251a3a;
  
  --primary: #a855f7;
  --primary-hover: #c084fc;
  --secondary: #ec4899;
  --accent: #f0abfc;
  
  --success: #10b981;
  --warning: #f59e0b;
  --error: #f43f5e;
  --info: #a855f7;
  
  --text-primary: #faf5ff;
  --text-secondary: #d8b4fe;
  --text-tertiary: #a78bfa;
  
  --border: #2e1a47;
  --border-hover: #3d2459;
  
  --gradient-primary: linear-gradient(135deg, #a855f7 0%, #ec4899 100%);
  --gradient-accent: linear-gradient(135deg, #f0abfc 0%, #fbbf24 100%);
}
```

### 6. 赛博朋克

**适用场景**: 酷炫展示、个性化  
**风格**: 未来感、霓虹

```css
:root[data-theme="cyberpunk"] {
  --background: #0a0e1a;
  --surface: #13162b;
  --surface-hover: #1c1f3c;
  
  --primary: #ff00ff;
  --primary-hover: #ff3cff;
  --secondary: #00ffff;
  --accent: #ffff00;
  
  --success: #00ff9f;
  --warning: #ffaa00;
  --error: #ff0055;
  --info: #00d9ff;
  
  --text-primary: #ffffff;
  --text-secondary: #b4b4ff;
  --text-tertiary: #7979ff;
  
  --border: #2d1f4a;
  --border-hover: #3d2f5a;
  
  --gradient-primary: linear-gradient(135deg, #ff00ff 0%, #00ffff 100%);
  --gradient-accent: linear-gradient(135deg, #ffff00 0%, #ff00ff 100%);
}
```

## 实现方案

### 1. CSS Variables（推荐）

```typescript
// lib/themes.ts
export const themes = {
  'tech-blue': { /* ... */ },
  'finance-dark': { /* ... */ },
  'minimal-light': { /* ... */ },
  'dark-green': { /* ... */ },
  'violet-dream': { /* ... */ },
  'cyberpunk': { /* ... */ }
}

export function applyTheme(themeName: string) {
  const root = document.documentElement
  const theme = themes[themeName]
  
  Object.entries(theme).forEach(([key, value]) => {
    root.style.setProperty(`--${key}`, value)
  })
  
  root.setAttribute('data-theme', themeName)
  localStorage.setItem('theme', themeName)
}
```

### 2. 主题切换器组件

```typescript
// components/theme-switcher.tsx
'use client'

import { useTheme } from '@/hooks/use-theme'
import { Palette } from 'lucide-react'

export function ThemeSwitcher() {
  const { theme, setTheme, themes } = useTheme()
  
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <Palette className="h-5 w-5" />
        </Button>
      </DropdownMenuTrigger>
      
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>选择主题</DropdownMenuLabel>
        <DropdownMenuSeparator />
        
        {themes.map((t) => (
          <DropdownMenuItem
            key={t.id}
            onClick={() => setTheme(t.id)}
            className="flex items-center justify-between"
          >
            <span>{t.name}</span>
            {theme === t.id && <Check className="h-4 w-4" />}
          </DropdownMenuItem>
        ))}
        
        <DropdownMenuSeparator />
        
        <DropdownMenuItem onClick={() => setTheme('auto')}>
          <Monitor className="mr-2 h-4 w-4" />
          跟随系统
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
```

### 3. 自动切换

```typescript
// hooks/use-theme.ts
export function useTheme() {
  const [theme, setThemeState] = useState<string>('tech-blue')
  
  useEffect(() => {
    // 从localStorage读取
    const saved = localStorage.getItem('theme')
    if (saved) {
      setThemeState(saved)
      applyTheme(saved)
    }
    
    // 监听系统主题变化
    if (saved === 'auto') {
      const matcher = window.matchMedia('(prefers-color-scheme: dark)')
      const listener = (e: MediaQueryListEvent) => {
        applyTheme(e.matches ? 'tech-blue' : 'minimal-light')
      }
      matcher.addEventListener('change', listener)
      return () => matcher.removeEventListener('change', listener)
    }
  }, [])
  
  const setTheme = (newTheme: string) => {
    setThemeState(newTheme)
    applyTheme(newTheme)
  }
  
  return { theme, setTheme, themes: THEME_LIST }
}
```

## 主题预览

在控制台右上角点击 🎨 图标即可切换主题，实时预览效果。

## 扩展自定义主题

用户可以在设置页面创建自定义主题：

1. 选择基础主题
2. 调整颜色参数
3. 保存为新主题
4. 导出/导入主题配置

## 最佳实践

1. **使用CSS Variables**: 所有组件使用CSS变量，不硬编码颜色
2. **语义化命名**: 使用 `--primary` 而不是 `--blue-500`
3. **渐变效果**: 提供预设渐变，保持视觉一致性
4. **辅助功能**: 确保所有主题满足 WCAG 2.1 AA 标准
