// 主布局 - App Layout（支持折叠）
'use client'

import { useState, useEffect } from 'react'
import { Sidebar } from './sidebar'
import { Header } from './header'
import {
  loadThemeSelection,
  saveThemeSelection,
  applyTheme,
  type ThemeId,
  type ThemeMode,
  type ThemeSelection,
} from '@/lib/theme'

interface AppLayoutProps {
  children: React.ReactNode
  title?: string
  subtitle?: string
}

const SIDEBAR_COLLAPSED_KEY = 'corn_sidebar_collapsed'

export function AppLayout({ children, title = '仪表概览', subtitle }: AppLayoutProps) {
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false
    try {
      return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true'
    } catch {
      return false
    }
  })

  const [theme, setTheme] = useState<ThemeSelection>(() => loadThemeSelection())
  const [isDarkMode, setIsDarkMode] = useState(false)

  useEffect(() => {
    const darkMode = applyTheme(theme)
    setIsDarkMode(darkMode)
    saveThemeSelection(theme)
  }, [theme])

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(collapsed))
    } catch {}
  }, [collapsed])

  const handleToggleCollapse = () => {
    setCollapsed(!collapsed)
  }

  const handleSelectPalette = (palette: ThemeId) => {
    setTheme(current => ({ ...current, palette }))
  }

  const handleSelectMode = (mode: ThemeMode) => {
    setTheme(current => ({ ...current, mode }))
  }

  return (
    <div className="h-dvh w-full overflow-hidden bg-background text-foreground flex">
      {/* 侧边导航 - 固定视口高度 */}
      <Sidebar collapsed={collapsed} onToggleCollapse={handleToggleCollapse} />

      {/* 右侧主工作区容器 - 视口锁定，仅内容区域滚动 */}
      <div className="flex-1 flex flex-col h-dvh min-w-0 overflow-hidden">
        {/* 顶部栏 - 固定在顶部 */}
        <Header
          title={title}
          subtitle={subtitle}
          theme={theme}
          isDarkMode={isDarkMode}
          onSelectPalette={handleSelectPalette}
          onSelectMode={handleSelectMode}
          collapsed={collapsed}
        />

        {/* 主内容区 - 独立垂直滚动 */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-5">
          <div className="max-w-[1440px] w-full mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
