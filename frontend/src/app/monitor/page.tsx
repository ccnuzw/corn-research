// 数据监控页面 - 实时数据展示和趋势分析
'use client'

import { useState, useEffect } from 'react'
import { AppLayout } from '@/components/layout/app-layout'
import { Breadcrumb } from '@/components/ui/breadcrumb'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { LineChart, Activity, TrendingUp, Database, RefreshCw, Filter } from 'lucide-react'
import { api } from '@/lib/api'

interface MarketData {
  id: string
  business_date: string
  indicator_name: string
  value: number
  unit: string
  source: string
  quality: string
  collected_at: string
}

interface DataStats {
  total_records: number
  indicator_count: number
  coverage_rate: number
  latest_collection: string | null
}

interface Indicator {
  name: string
  display_name: string
  unit: string
  record_count: number
}

export default function MonitorPage() {
  const [data, setData] = useState<MarketData[]>([])
  const [stats, setStats] = useState<DataStats | null>(null)
  const [indicators, setIndicators] = useState<Indicator[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedIndicator, setSelectedIndicator] = useState<string>('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 20

  // 加载数据
  const loadData = async () => {
    try {
      setLoading(true)
      
      // 并行加载所有数据
      const [dataResult, statsResult, indicatorsResult] = await Promise.all([
        api.getLatestData(undefined, 30, 100),
        api.getStats(),
        api.getIndicators(),
      ])

      setData(dataResult as unknown as MarketData[] || [])
      setStats(statsResult as unknown as DataStats | null)
      setIndicators(indicatorsResult as unknown as Indicator[] || [])
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 30000) // 每30秒刷新
    return () => clearInterval(interval)
  }, [])

  // 过滤数据
  const filteredData = data.filter(item => {
    const matchesIndicator = selectedIndicator === 'all' || item.indicator_name === selectedIndicator
    const matchesSearch = searchTerm === '' || 
      item.indicator_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.source.toLowerCase().includes(searchTerm.toLowerCase())
    return matchesIndicator && matchesSearch
  })

  // 分页
  const totalPages = Math.ceil(filteredData.length / itemsPerPage)
  const paginatedData = filteredData.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  )

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('zh-CN')
  }

  const formatBusinessDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('zh-CN')
  }

  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'A': return 'bg-green-100 text-green-800'
      case 'B': return 'bg-blue-100 text-blue-800'
      case 'C': return 'bg-yellow-100 text-yellow-800'
      case 'D': return 'bg-red-100 text-red-800'
      default: return 'bg-muted text-gray-800'
    }
  }

  return (
    <AppLayout title="数据监控">
      <div className="space-y-4">
        {/* 面包屑 */}
        <Breadcrumb
          items={[
            { label: '控制台', href: '/' },
            { label: '数据监控', icon: <LineChart className="w-4 h-4" /> },
          ]}
        />

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                总记录数
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold font-mono">
                {stats?.total_records.toLocaleString() || '0'}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                <Database className="w-3 h-3 inline mr-1" />
                条数据记录
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                监测指标
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold font-mono">
                {stats?.indicator_count || 0}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                <Activity className="w-3 h-3 inline mr-1" />
                个活跃指标
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                数据覆盖率
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold font-mono">
                {stats?.coverage_rate.toFixed(1) || '0.0'}%
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                <TrendingUp className="w-3 h-3 inline mr-1" />
                数据完整度
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                最新更新
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm font-medium">
                {stats?.latest_collection ? formatDate(stats.latest_collection) : '-'}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                <RefreshCw className="w-3 h-3 inline mr-1" />
                最后采集时间
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 指标概览 */}
        <Card>
          <CardHeader>
            <CardTitle>指标统计</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {indicators.map((indicator) => (
                <div
                  key={indicator.name}
                  className="p-4 bg-card border border-border rounded-lg hover:border-primary/50 transition-colors"
                >
                  <div className="font-medium text-card-foreground">{indicator.display_name}</div>
                  <div className="text-sm text-muted-foreground mt-1">{indicator.unit}</div>
                  <div className="text-2xl font-bold font-mono mt-2">
                    {indicator.record_count}
                  </div>
                  <div className="text-xs text-muted-foreground">条记录</div>
                </div>
              ))}
              {indicators.length === 0 && (
                <div className="col-span-3 text-center text-muted-foreground py-8">
                  暂无指标数据
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* 数据表格 */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>最新数据</CardTitle>
              <Button size="sm" variant="outline" onClick={loadData}>
                <RefreshCw className="w-4 h-4 mr-1" />
                刷新
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {/* 过滤器 */}
            <div className="flex items-center gap-3 mb-4">
              <div className="flex-1">
                <Input
                  placeholder="搜索指标或来源..."
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value)
                    setCurrentPage(1)
                  }}
                />
              </div>
              <div className="w-48 shrink-0">
                <Select
                  value={selectedIndicator}
                  onValueChange={(value) => {
                    setSelectedIndicator(value)
                    setCurrentPage(1)
                  }}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全部指标</SelectItem>
                    {indicators.map((indicator) => (
                      <SelectItem key={indicator.name} value={indicator.name}>
                        {indicator.display_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* 表格 */}
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-border">
                <thead className="bg-muted/30">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">
                      业务日期
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">
                      指标名称
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase">
                      数值
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">
                      来源
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">
                      质量
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">
                      采集时间
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-card divide-y divide-border">
                  {loading ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-sm text-muted-foreground">
                        加载中...
                      </td>
                    </tr>
                  ) : paginatedData.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-sm text-muted-foreground">
                        暂无数据
                      </td>
                    </tr>
                  ) : (
                    paginatedData.map((item) => (
                      <tr key={item.id} className="hover:bg-muted/30">
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-card-foreground">
                          {formatBusinessDate(item.business_date)}
                        </td>
                        <td className="px-4 py-3 text-sm font-medium text-card-foreground">
                          {item.indicator_name}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-card-foreground text-right font-mono">
                          {item.value.toLocaleString()} {item.unit}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-muted-foreground">
                          <Badge variant="outline">{item.source}</Badge>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className={`text-xs px-2 py-1 rounded ${getQualityColor(item.quality)}`}>
                            {item.quality}
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-xs text-muted-foreground">
                          {formatDate(item.collected_at)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* 分页 */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4 pt-4 border-t">
                <div className="text-sm text-muted-foreground">
                  显示 {(currentPage - 1) * itemsPerPage + 1} - {Math.min(currentPage * itemsPerPage, filteredData.length)} 条，
                  共 {filteredData.length} 条
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={currentPage === 1}
                    onClick={() => setCurrentPage(currentPage - 1)}
                  >
                    上一页
                  </Button>
                  <div className="flex items-center px-3 text-sm">
                    第 {currentPage} / {totalPages} 页
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={currentPage === totalPages}
                    onClick={() => setCurrentPage(currentPage + 1)}
                  >
                    下一页
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  )
}
