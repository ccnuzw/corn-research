// 来源对比图组件
'use client'

import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Database, RefreshCw } from 'lucide-react'

interface SourceData {
  source: string
  count: number
}

export function SourceChart() {
  const [data, setData] = useState<SourceData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // TODO: 替换为真实API调用
      // const response = await fetch('http://localhost:18000/api/stats/sources')
      // const result = await response.json()
      // setData(result.data || [])
      
      // 临时模拟数据
      const mockData: SourceData[] = [
        { source: '博亚和讯', count: 128 },
        { source: '新浪财经', count: 95 },
        { source: '大连商品交易所', count: 67 },
        { source: '郑州商品交易所', count: 52 },
        { source: '国家统计局', count: 38 },
      ]
      setData(mockData)
    } catch (err) {
      console.error('Failed to load source data:', err)
      setError('加载数据源统计失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5" />
            数据源分布
          </CardTitle>
          <CardDescription>各数据源采集记录数对比</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center">
            <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5" />
            数据源分布
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-destructive">
            {error}
          </div>
        </CardContent>
      </Card>
    )
  }

  const total = data.reduce((sum, item) => sum + item.count, 0)

  return (
    <Card className="card-in">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="w-5 h-5" />
          数据源分布
        </CardTitle>
        <CardDescription>各数据源采集记录数对比，共 {total} 条</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] chart-fade">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <defs>
                <linearGradient id="colorBar" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--chart-2))" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="hsl(var(--chart-2))" stopOpacity={0.3}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border-muted))" />
              <XAxis
                dataKey="source"
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                angle={-15}
                textAnchor="end"
                height={80}
              />
              <YAxis
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px',
                }}
                formatter={(value) => [`${value ?? 0} 条`, '记录数']}
              />
              <Bar
                dataKey="count"
                fill="url(#colorBar)"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
