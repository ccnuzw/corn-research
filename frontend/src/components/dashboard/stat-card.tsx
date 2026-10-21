// 统计卡片 - 参照 kiro.rs 设计（更精致紧凑）
'use client'

import { Card } from '@/components/ui/card'
import { cn, formatNumber, formatPercent } from '@/lib/utils'
import { TrendingUp, TrendingDown } from 'lucide-react'

interface StatCardProps {
  title: string
  value: number | string
  unit?: string
  trend?: number
  icon?: React.ReactNode
  description?: string
  loading?: boolean
  decimals?: number
}

export function StatCard({
  title,
  value,
  unit,
  trend,
  icon,
  description,
  loading = false,
  decimals = 0,
}: StatCardProps) {
  const numericValue = typeof value === 'number' ? value : parseFloat(value)
  const trendIsPositive = trend && trend > 0
  const trendIsNegative = trend && trend < 0

  return (
    <Card className={cn(
      'relative overflow-hidden p-5 transition-all card-in',
      'hover:shadow-lg hover:scale-[1.01]'
    )}>
      {/* 左上角图标 - 更小 */}
      {icon && (
        <div className="absolute top-3 right-3 opacity-10">
          <div className="text-3xl">{icon}</div>
        </div>
      )}

      {/* 标题 - 更小的字体 */}
      <div className="mb-2.5">
        <h3 className="text-[12px] font-medium text-muted-foreground leading-tight">
          {title}
        </h3>
        {description && (
          <p className="text-[11px] text-muted-foreground/80 mt-0.5">{description}</p>
        )}
      </div>

      {/* 数值 - 稍小 */}
      <div className="flex items-baseline gap-1.5">
        {loading ? (
          <div className="h-10 w-28 bg-muted animate-pulse rounded" />
        ) : (
          <>
            <div className="text-3xl font-bold font-mono text-foreground leading-none">
              {typeof value === 'number' ? formatNumber(numericValue, decimals) : value}
            </div>
            {unit && (
              <span className="text-base text-muted-foreground">{unit}</span>
            )}
          </>
        )}
      </div>

      {/* 趋势指示 - 更紧凑 */}
      {trend !== undefined && !loading && (
        <div className="mt-2 flex items-center gap-1">
          {trendIsPositive && (
            <>
              <TrendingUp className="h-3.5 w-3.5 text-green-500" />
              <span className="text-[11px] text-green-500 font-medium">
                {formatPercent(trend)}
              </span>
            </>
          )}
          {trendIsNegative && (
            <>
              <TrendingDown className="h-3.5 w-3.5 text-red-500" />
              <span className="text-[11px] text-red-500 font-medium">
                {formatPercent(trend)}
              </span>
            </>
          )}
          {!trendIsPositive && !trendIsNegative && (
            <span className="text-[11px] text-muted-foreground">
              持平
            </span>
          )}
          <span className="text-[10px] text-muted-foreground/70">vs 昨日</span>
        </div>
      )}
    </Card>
  )
}

// 统计卡片网格容器 - 更小间距
export function StatCardGrid({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {children}
    </div>
  )
}
