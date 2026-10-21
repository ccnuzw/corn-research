// 顶部标题栏 - 参照 kiro.rs 设计（更精致）
'use client'

import { ThemePicker } from '@/components/theme-picker'
import { Activity, Zap, Heart, RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { type ThemeSelection } from '@/lib/theme'

interface HeaderProps {
  title: string
  subtitle?: string
  theme: ThemeSelection
  isDarkMode: boolean
  onSelectPalette: (palette: any) => void
  onSelectMode: (mode: any) => void
  collapsed: boolean
}

export function Header({
  title,
  subtitle,
  theme,
  isDarkMode,
  onSelectPalette,
  onSelectMode,
  collapsed,
}: HeaderProps) {
  return (
    <header className="h-16 shrink-0 flex items-center justify-between gap-2 border-b border-border/60 bg-card px-4 sm:px-6 z-20">
      {/* 左侧：标题 - 更紧凑 */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="min-w-0">
          <h1 className="text-sm font-semibold text-foreground leading-none truncate">{title}</h1>
          {subtitle && (
            <p className="text-xs text-muted-foreground mt-1 truncate">{subtitle}</p>
          )}
        </div>
      </div>

      {/* 右侧：状态指示器和工具栏 - 更小 */}
      <div className="flex items-center gap-2 shrink-0">
        {/* 状态指示器 - 更紧凑 */}
        <div className="hidden lg:flex items-center gap-1.5 mr-3">
          <Badge variant="outline" className="gap-1 px-2 py-0.5 text-[11px]">
            <Activity className="h-3 w-3 text-green-500" />
            <span>均衡负载</span>
          </Badge>
          <Badge variant="outline" className="gap-1 px-2 py-0.5 text-[11px]">
            <Zap className="h-3 w-3 text-blue-500" />
            <span>故障转移·30m</span>
          </Badge>
          <Badge variant="success" className="gap-1 px-2 py-0.5 text-[11px]">
            <Heart className="h-3 w-3" />
            <span>自愈开</span>
          </Badge>
        </div>

        {/* 分隔线 */}
        <div className="hidden sm:block h-5 w-px bg-border" />

        {/* 工具按钮 - 更小 */}
        <Button variant="ghost" size="icon" className="h-8 w-8" title="刷新">
          <RefreshCw className="h-4 w-4" />
        </Button>

        {/* 主题选择器 */}
        <ThemePicker
          theme={theme}
          isDarkMode={isDarkMode}
          onSelectPalette={onSelectPalette}
          onSelectMode={onSelectMode}
        />
      </div>
    </header>
  )
}
