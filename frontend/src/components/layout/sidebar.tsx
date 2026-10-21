// 侧边导航栏 - 完全参照 kiro.rs 设计（选中状态+间距优化+折叠功能）
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Database,
  LineChart,
  Shield,
  Settings,
  Clock,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
} from 'lucide-react'
import { useState } from 'react'

interface NavItem {
  label: string
  icon: React.ElementType
  href: string
  children?: NavItem[]
}

const NAV_ITEMS: NavItem[] = [
  {
    label: '仪表概览',
    icon: LayoutDashboard,
    href: '/',
  },
  {
    label: '采集器管理',
    icon: Database,
    href: '/collectors',
  },
  {
    label: '定时任务',
    icon: Clock,
    href: '/scheduler',
  },
  {
    label: '数据监控',
    icon: LineChart,
    href: '/monitor',
  },
  {
    label: '数据质量',
    icon: Shield,
    href: '/quality',
  },
  {
    label: '系统设置',
    icon: Settings,
    href: '/settings',
    children: [
      { label: '数据源配置', icon: Database, href: '/settings/sources' },
      { label: '主题设置', icon: Settings, href: '/settings/theme' },
      { label: '系统日志', icon: LineChart, href: '/settings/logs' },
    ],
  },
]

interface SidebarProps {
  collapsed: boolean
  onToggleCollapse: () => void
}

export function Sidebar({ collapsed, onToggleCollapse }: SidebarProps) {
  const pathname = usePathname()
  const [expandedItems, setExpandedItems] = useState<string[]>(['/settings'])

  const toggleExpand = (href: string) => {
    setExpandedItems(prev =>
      prev.includes(href) ? prev.filter(h => h !== href) : [...prev, href]
    )
  }

  const isActive = (href: string) => {
    return pathname === href || pathname?.startsWith(href + '/')
  }

  return (
    <aside className={cn(
      "fixed inset-y-0 left-0 z-50 flex h-dvh flex-col shrink-0 border-r border-border/60 bg-card transition-[width] duration-200 lg:relative",
      collapsed ? "w-[68px]" : "w-[200px]"
    )}>
      {/* Logo - 折叠时只显示图标 */}
      <div className="h-16 shrink-0 flex items-center px-4 border-b border-border/60">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div className="w-7 h-7 rounded-md bg-primary/10 flex items-center justify-center shrink-0">
            <span className="text-base font-bold text-primary">🌽</span>
          </div>
          {!collapsed && (
            <span className="text-sm font-semibold text-foreground whitespace-nowrap">玉米研究</span>
          )}
        </div>
      </div>

      {/* Navigation - 折叠时隐藏文字 */}
      <nav className="flex-1 overflow-y-auto px-3 py-3">
        <ul className="space-y-1">
          {NAV_ITEMS.map(item => (
            <NavItemComponent
              key={item.href}
              item={item}
              isActive={isActive(item.href)}
              isExpanded={expandedItems.includes(item.href)}
              onToggleExpand={() => toggleExpand(item.href)}
              pathname={pathname}
              collapsed={collapsed}
            />
          ))}
        </ul>
      </nav>

      {/* Footer - 折叠按钮 */}
      <div className="p-3 border-t border-border/60 shrink-0">
        {!collapsed && (
          <div className="flex items-center justify-between text-[11px] text-muted-foreground mb-2">
            <span>V2.0.0</span>
            <span>Alpha</span>
          </div>
        )}
        <button
          onClick={onToggleCollapse}
          className="w-full flex items-center justify-center h-8 rounded-md hover:bg-accent transition-colors"
          title={collapsed ? "展开侧边栏" : "收起侧边栏"}
        >
          <ChevronLeft className={cn(
            "w-4 h-4 text-muted-foreground transition-transform",
            collapsed && "rotate-180"
          )} />
        </button>
      </div>
    </aside>
  )
}

interface NavItemComponentProps {
  item: NavItem
  isActive: boolean
  isExpanded: boolean
  onToggleExpand: () => void
  pathname: string | null
  collapsed: boolean
}

function NavItemComponent({
  item,
  isActive,
  isExpanded,
  onToggleExpand,
  pathname,
  collapsed,
}: NavItemComponentProps) {
  const Icon = item.icon
  const hasChildren = item.children && item.children.length > 0

  // 折叠时只显示图标
  if (collapsed) {
    return (
      <li>
        <Link
          href={item.href}
          className={cn(
            'flex items-center justify-center h-10 rounded-xl text-[13px] font-medium transition-colors',
            'hover:bg-accent hover:text-accent-foreground',
            isActive 
              ? 'bg-accent text-accent-foreground shadow-sm' 
              : 'text-foreground'
          )}
          title={item.label}
        >
          <Icon className="w-5 h-5 shrink-0" />
        </Link>
      </li>
    )
  }

  return (
    <li>
      {hasChildren ? (
        <>
          <button
            onClick={onToggleExpand}
            className={cn(
              'w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-medium transition-colors',
              'hover:bg-accent hover:text-accent-foreground',
              isActive 
                ? 'bg-accent text-accent-foreground shadow-sm' 
                : 'text-foreground'
            )}
          >
            <Icon className="w-4 h-4 shrink-0" />
            <span className="flex-1 text-left">{item.label}</span>
            {isExpanded ? (
              <ChevronDown className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
            )}
          </button>
          {isExpanded && (
            <ul className="ml-7 mt-1 space-y-0.5 border-l border-border/50 pl-3">
              {item.children?.map(child => {
                const ChildIcon = child.icon
                const childActive = pathname === child.href
                return (
                  <li key={child.href}>
                    <Link
                      href={child.href}
                      className={cn(
                        'flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[12px] transition-colors',
                        'hover:bg-accent/50 hover:text-accent-foreground',
                        childActive
                          ? 'bg-accent/50 text-accent-foreground font-medium'
                          : 'text-muted-foreground'
                      )}
                    >
                      <ChildIcon className="w-3.5 h-3.5 shrink-0" />
                      <span>{child.label}</span>
                    </Link>
                  </li>
                )
              })}
            </ul>
          )}
        </>
      ) : (
        <Link
          href={item.href}
          className={cn(
            'flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-medium transition-colors',
            'hover:bg-accent hover:text-accent-foreground',
            isActive 
              ? 'bg-accent text-accent-foreground shadow-sm' 
              : 'text-foreground'
          )}
        >
          <Icon className="w-4 h-4 shrink-0" />
          <span>{item.label}</span>
        </Link>
      )}
    </li>
  )
}
