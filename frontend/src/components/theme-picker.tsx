// 主题选择器 - 完全参照 kiro.rs/theme-picker.tsx
'use client'

import { Check, Monitor, Moon, Palette, Sun } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  THEME_METADATA,
  type ThemeId,
  type ThemeMode,
  type ThemeSelection,
} from '@/lib/theme'
import { useState } from 'react'

const MODE_OPTIONS: readonly {
  id: ThemeMode
  label: string
  icon: typeof Monitor
}[] = [
  { id: 'system', label: '跟随系统', icon: Monitor },
  { id: 'light', label: '浅色', icon: Sun },
  { id: 'dark', label: '深色', icon: Moon },
]

interface ThemePickerProps {
  theme: ThemeSelection
  isDarkMode: boolean
  onSelectPalette: (palette: ThemeId) => void
  onSelectMode: (mode: ThemeMode) => void
}

export function ThemePicker({
  theme,
  isDarkMode,
  onSelectPalette,
  onSelectMode,
}: ThemePickerProps) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setIsOpen(!isOpen)}
        className="relative"
      >
        <Palette className="h-5 w-5" />
        <span className="sr-only">切换主题</span>
      </Button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 top-12 z-50 min-w-[300px] rounded-lg border bg-popover p-4 shadow-lg animate-in fade-in-0 zoom-in-95">
            {/* 主题色板 */}
            <div className="space-y-3">
              <div className="text-sm font-semibold text-foreground">配色主题</div>
              <div className="grid grid-cols-2 gap-2">
                {THEME_METADATA.map(({ id, name, description }) => (
                  <button
                    key={id}
                    onClick={() => onSelectPalette(id)}
                    className={cn(
                      'relative flex flex-col items-start gap-2 rounded-md border-2 p-3 text-left transition-all',
                      'hover:border-primary/50 hover:bg-accent/50',
                      theme.palette === id
                        ? 'border-primary bg-accent/50'
                        : 'border-border'
                    )}
                  >
                    <div className="flex w-full items-center justify-between">
                      <span className="text-sm font-medium">{name}</span>
                      {theme.palette === id && (
                        <Check className="h-4 w-4 text-primary" />
                      )}
                    </div>
                    <div className="flex gap-1">
                      {getThemePreviewColors(id).map((color, i) => (
                        <div
                          key={i}
                          className="h-5 w-5 rounded-sm"
                          style={{ backgroundColor: color }}
                        />
                      ))}
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {description}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* 明暗模式 */}
            <div className="mt-4 space-y-3 border-t pt-4">
              <div className="text-sm font-semibold text-foreground">明暗模式</div>
              <div className="grid grid-cols-3 gap-1 rounded-md bg-muted p-1">
                {MODE_OPTIONS.map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    onClick={() => onSelectMode(id)}
                    className={cn(
                      'flex flex-col items-center justify-center gap-1 rounded-sm px-1 py-2 text-xs transition-all',
                      theme.mode === id
                        ? 'bg-card text-primary shadow-sm'
                        : 'text-muted-foreground hover:text-foreground'
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// 获取主题预览色板
function getThemePreviewColors(themeId: ThemeId): string[] {
  const colorMap: Record<ThemeId, string[]> = {
    system: ['#7ce3cb', '#5dd3b8', '#3ec3a5', '#1fb392'],
    graphite: ['#94a3b8', '#64748b', '#475569', '#334155'],
    ocean: ['#3b82f6', '#2563eb', '#1d4ed8', '#1e40af'],
    forest: ['#10b981', '#059669', '#047857', '#065f46'],
    amber: ['#f59e0b', '#d97706', '#b45309', '#92400e'],
  }
  return colorMap[themeId]
}
