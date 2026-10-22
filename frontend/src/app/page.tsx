// Dashboard 仪表盘页面 - 完全参照 kiro.rs 设计
'use client'

import { useEffect, useState } from 'react'
import { AppLayout } from '@/components/layout/app-layout'
import { StatCard, StatCardGrid } from '@/components/dashboard/stat-card'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { api, type CollectorInfo, type DataStats, type MarketData } from '@/lib/api'
import {
  Database,
  TrendingUp,
  Activity,
  PlayCircle,
  Clock,
  AlertCircle,
} from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { TrendChart, QualityChart, SourceChart, TimelineChart } from '@/components/charts'

export default function DashboardPage() {
  const [stats, setStats] = useState<DataStats | null>(null)
  const [collectors, setCollectors] = useState<CollectorInfo[]>([])
  const [trendData, setTrendData] = useState<MarketData[]>([])
  const [trendDays, setTrendDays] = useState(7)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const loadData = async () => {
      setLoading(true)
      try {
        const [statsData, collectorsData, trendsData] = await Promise.all([
          api.getStats(),
          api.getCollectors(),
          api.getTrendData('corn_price', trendDays),
        ])
        if (cancelled) return
        if (!statsData.success || !statsData.data) {
          throw new Error(statsData.message || '加载统计数据失败')
        }
        if (!collectorsData.success || !collectorsData.data) {
          throw new Error(collectorsData.message || '加载采集器失败')
        }
        if (!trendsData.success || !trendsData.data) {
          throw new Error(trendsData.message || '加载趋势数据失败')
        }
        setStats(statsData.data)
        setCollectors(collectorsData.data)
        setTrendData(trendsData.data)
        setError(null)
      } catch (err) {
        if (cancelled) return
        console.error('Failed to load dashboard data:', err)
        setError(err instanceof Error ? err.message : '加载数据失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadData()
    return () => { cancelled = true }
  }, [trendDays])

  return (
    <AppLayout title="仪表概览" subtitle="玉米研究系统运行状态">
      <div className="space-y-6">
        {/* 错误提示 */}
        {error && (
          <Card className="border-destructive">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3 text-destructive">
                <AlertCircle className="h-5 w-5" />
                <div>
                  <p className="font-medium">无法加载数据</p>
                  <p className="text-sm text-muted-foreground">{error}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 统计卡片 */}
        <StatCardGrid>
          <StatCard
            title="总数据量"
            value={stats?.total_records ?? 0}
            unit="条"
            icon={<Database />}
            description="截至今日"
            loading={loading}
          />
          <StatCard
            title="数据指标"
            value={stats?.indicator_count ?? 0}
            unit="个"
            icon={<TrendingUp />}
            description="已采集指标数量"
            loading={loading}
          />
          <StatCard
            title="活跃采集器"
            value={collectors.filter(collector => collector.status === 'running').length}
            unit="个"
            icon={<Activity />}
            description="正在运行"
            loading={loading}
          />
          <StatCard
            title="最近采集"
            value={stats?.latest_collection ? new Date(stats.latest_collection).toLocaleDateString('zh-CN') : '暂无记录'}
            icon={<Clock />}
            description="最近一次数据入库日期"
            loading={loading}
          />
        </StatCardGrid>

        {/* 趋势图表 */}
        <Card className="card-in">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>玉米价格趋势</CardTitle>
                <CardDescription>最近{trendDays}天指标值变化</CardDescription>
              </div>
              <div className="flex gap-2">
                {[7, 30, 90].map(days => (
                  <Button key={days} variant={trendDays === days ? 'default' : 'outline'} size="sm" onClick={() => setTrendDays(days)}>{days}天</Button>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] chart-fade">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData}>
                  <defs>
                    <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(var(--chart-1))" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="hsl(var(--chart-1))" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border-muted))" />
                  <XAxis
                    dataKey="business_date"
                    stroke="hsl(var(--muted-foreground))"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    stroke="hsl(var(--muted-foreground))"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(value) => `${value}`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '6px',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="hsl(var(--chart-1))"
                    fill="url(#colorValue)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* 数据可视化图表 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <TrendChart />
          <QualityChart />
          <SourceChart />
          <TimelineChart />
        </div>

        {/* 采集器状态列表 */}
        <Card className="card-in">
          <CardHeader>
            <CardTitle>采集器状态</CardTitle>
            <CardDescription>所有数据源实时监控</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {collectors.map((collector) => (
                <div
                  key={collector.id}
                  className="flex items-center justify-between p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    {/* 状态图标 */}
                    <div className="flex-shrink-0">
                      {collector.status === 'running' && (
                        <PlayCircle className="h-5 w-5 text-green-500" />
                      )}
                      {collector.status === 'idle' && (
                        <Clock className="h-5 w-5 text-blue-500" />
                      )}
                      {collector.status === 'failed' && (
                        <AlertCircle className="h-5 w-5 text-red-500" />
                      )}
                    </div>

                    {/* 采集器信息 */}
                    <div>
                      <div className="font-medium">{collector.name}</div>
                      <div className="text-sm text-muted-foreground">
                        上次运行: {collector.last_run || '未运行'}
                      </div>
                    </div>
                  </div>

                  {/* 右侧信息 */}
                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <div className="text-sm font-mono font-semibold">
                        {collector.success_rate || 0}%
                      </div>
                      <div className="text-xs text-muted-foreground">成功率</div>
                    </div>

                    <Badge
                      variant={
                        collector.status === 'running'
                          ? 'success'
                          : collector.status === 'failed'
                          ? 'destructive'
                          : 'secondary'
                      }
                    >
                      {collector.status === 'running' && '运行中'}
                      {collector.status === 'idle' && '空闲'}
                      {collector.status === 'failed' && '错误'}
                    </Badge>

                    <Button variant="outline" size="sm">
                      查看详情
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  )
}
