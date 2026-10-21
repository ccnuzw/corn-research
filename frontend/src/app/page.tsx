// Dashboard 仪表盘页面 - 完全参照 kiro.rs 设计
'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { AppLayout } from '@/components/layout/app-layout'
import { StatCard, StatCardGrid } from '@/components/dashboard/stat-card'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { api, type CollectorInfo, type SystemStats } from '@/lib/api'
import {
  Database,
  TrendingUp,
  Activity,
  CheckCircle2,
  PlayCircle,
  Clock,
  AlertCircle,
} from 'lucide-react'
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function DashboardPage() {
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [collectors, setCollectors] = useState<CollectorInfo[]>([])
  const [trendData, setTrendData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadData = async () => {
      try {
        const [statsData, collectorsData, trendsData] = await Promise.all([
          api.getStats(),
          api.getCollectors(),
          api.getTrendData('corn_price', 7), // 修复：getTrendData 需要 indicator 参数
        ])
        setStats(statsData)
        setCollectors(collectorsData)
        setTrendData(trendsData)
        setError(null)
      } catch (err) {
        console.error('Failed to load dashboard data:', err)
        setError(err instanceof Error ? err.message : '加载数据失败')
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

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
            value={stats?.totalRecords || 0}
            unit="条"
            trend={12.5}
            icon={<Database />}
            description="截至今日"
            loading={loading}
          />
          <StatCard
            title="今日采集"
            value={stats?.todayCollected || 0}
            unit="条"
            trend={8.3}
            icon={<TrendingUp />}
            description="最近24小时"
            loading={loading}
          />
          <StatCard
            title="活跃采集器"
            value={stats?.activeCollectors || 0}
            unit="个"
            icon={<Activity />}
            description="正在运行"
            loading={loading}
          />
          <StatCard
            title="数据质量"
            value={stats?.dataQuality || 0}
            unit="%"
            trend={2.1}
            icon={<CheckCircle2 />}
            description="质量评分"
            loading={loading}
            decimals={1}
          />
        </StatCardGrid>

        {/* 趋势图表 */}
        <Card className="card-in">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>数据采集趋势</CardTitle>
                <CardDescription>最近7天采集量变化</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm">7天</Button>
                <Button variant="outline" size="sm">30天</Button>
                <Button variant="outline" size="sm">90天</Button>
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
                    dataKey="date"
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
                      {collector.status === 'error' && (
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
                          : collector.status === 'error'
                          ? 'destructive'
                          : 'secondary'
                      }
                    >
                      {collector.status === 'running' && '运行中'}
                      {collector.status === 'idle' && '空闲'}
                      {collector.status === 'error' && '错误'}
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
