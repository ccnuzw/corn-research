// 质量分布图组件
'use client'

import { useEffect, useState } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Shield, RefreshCw } from 'lucide-react'

interface QualityData {
  grade: string
  count: number
}

const COLORS = {
  'A': 'hsl(var(--chart-1))',
  'B': 'hsl(var(--chart-2))',
  'C': 'hsl(var(--chart-3))',
  'D': 'hsl(var(--chart-4))',
}

export function QualityChart() {
  const [data, setData] = useState<QualityData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // TODO: 替换为真实API调用
      // const response = await fetch('http://localhost:18000/api/stats/quality')
      // const result = await response.json()
      // setData(result.data || [])
      
      // 临时模拟数据
      const mockData: QualityData[] = [
        { grade: 'A', count: 45 },
        { grade: 'B', count: 106 },
        { grade: 'C', count: 32 },
        { grade: 'D', count: 12 },
      ]
      setData(mockData)
    } catch (err) {
      console.error('Failed to load quality data:', err)
      setError('加载质量数据失败')
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
            <Shield className="w-5 h-5" />
            数据质量分布
          </CardTitle>
          <CardDescription>按质量等级统计</CardDescription>
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
            <Shield className="w-5 h-5" />
            数据质量分布
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
          <Shield className="w-5 h-5" />
          数据质量分布
        </CardTitle>
        <CardDescription>按质量等级统计，共 {total} 条记录</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] chart-fade">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                labelLine={false}
                nameKey="grade"
                label={({ name, value, percent }) =>
                  `${name}级 ${value} (${((percent ?? 0) * 100).toFixed(0)}%)`
                }
                outerRadius={80}
                fill="#8884d8"
                dataKey="count"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[entry.grade as keyof typeof COLORS] || COLORS.D} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px',
                }}
                formatter={(value, name) => {
                  const count = Number(value ?? 0)
                  const percent = (total > 0 ? (count / total) * 100 : 0).toFixed(1)
                  return [`${count} 条 (${percent}%)`, `${name}级`]
                }}
              />
              <Legend
                verticalAlign="bottom"
                height={36}
                formatter={(value, entry: any) => {
                  const item = data.find(d => d.grade === entry.payload.grade)
                  return `${entry.payload.grade}级: ${item?.count || 0}`
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
