// 数据采集监控页面
'use client'

import { useState, useEffect } from 'react'
import { AppLayout } from '@/components/layout/app-layout'
import { Breadcrumb } from '@/components/ui/breadcrumb'
import { Badge } from '@/components/ui/badge'
import { LineChart, Database, TrendingUp, Activity } from 'lucide-react'
import { api, type CollectionRecord } from '@/lib/api'

export default function CollectionPage() {
  const [records, setRecords] = useState<CollectionRecord[]>([])
  const [loading, setLoading] = useState(true)

  const loadRecords = async () => {
    try {
      setLoading(true)
      // 查询最近的采集记录
      const response = await api.queryRecords({ limit: 50 })
      if (response.success && response.data) {
        setRecords(response.data)
      }
    } catch (err) {
      console.error('Failed to load records:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRecords()
    const interval = setInterval(loadRecords, 10000) // 每10秒刷新
    return () => clearInterval(interval)
  }, [])

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('zh-CN')
  }

  const formatTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleTimeString('zh-CN')
  }

  return (
    <AppLayout title="数据采集">
      <div className="space-y-4">
        {/* 面包屑 */}
        <Breadcrumb
          items={[
            { label: '控制台', href: '/' },
            { label: '数据采集', icon: <Database className="w-4 h-4" /> },
          ]}
        />

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="rounded-lg border border-border/60 bg-card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <Database className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <div className="text-2xl font-bold">{records.length}</div>
                <div className="text-xs text-muted-foreground">总记录数</div>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-border/60 bg-card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-green-500" />
              </div>
              <div>
                <div className="text-2xl font-bold">
                  {records.filter(r => r.quality_grade === 'A').length}
                </div>
                <div className="text-xs text-muted-foreground">A级数据</div>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-border/60 bg-card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-orange-500/10 flex items-center justify-center">
                <Activity className="w-5 h-5 text-orange-500" />
              </div>
              <div>
                <div className="text-2xl font-bold">
                  {new Set(records.map(r => r.business_date)).size}
                </div>
                <div className="text-xs text-muted-foreground">数据天数</div>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-border/60 bg-card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <LineChart className="w-5 h-5 text-purple-500" />
              </div>
              <div>
                <div className="text-2xl font-bold">
                  {new Set(records.map(r => r.adapter_id)).size}
                </div>
                <div className="text-xs text-muted-foreground">活跃采集器</div>
              </div>
            </div>
          </div>
        </div>

        {/* 数据表格 */}
        <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
          <div className="p-5 border-b border-border/60">
            <h3 className="text-base font-semibold">最近采集记录</h3>
            <p className="text-sm text-muted-foreground mt-1">实时更新，每10秒刷新</p>
          </div>

          {loading && records.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground">
              <Activity className="w-8 h-8 animate-spin mx-auto mb-2" />
              加载中...
            </div>
          ) : records.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground">
              <Database className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>暂无采集记录</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-muted/50">
                  <tr className="h-11">
                    <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                      业务日期
                    </th>
                    <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                      主题
                    </th>
                    <th className="px-4 text-right text-[12px] font-medium text-muted-foreground">
                      数值
                    </th>
                    <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                      单位
                    </th>
                    <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                      质量
                    </th>
                    <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                      采集器
                    </th>
                    <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                      采集时间
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((record) => (
                    <tr
                      key={record.id}
                      className="h-12 border-b border-border hover:bg-accent/50 transition-colors"
                    >
                      <td className="px-4 text-[13px] font-mono">
                        {formatDate(record.business_date)}
                      </td>
                      <td className="px-4 text-[13px]">{record.topic_name || '-'}</td>
                      <td className="px-4 text-right text-[13px] font-mono font-semibold">
                        {record.value?.toFixed(2) || '-'}
                      </td>
                      <td className="px-4 text-[13px] text-muted-foreground">
                        {record.unit || '-'}
                      </td>
                      <td className="px-4">
                        {record.quality_grade ? (
                          <Badge
                            variant={
                              record.quality_grade === 'A'
                                ? 'success'
                                : record.quality_grade === 'B'
                                ? 'default'
                                : 'secondary'
                            }
                            className="rounded-full"
                          >
                            {record.quality_grade}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground text-[13px]">-</span>
                        )}
                      </td>
                      <td className="px-4 text-[13px] text-muted-foreground font-mono">
                        {record.adapter_id.substring(0, 20)}...
                      </td>
                      <td className="px-4 text-[13px] text-muted-foreground">
                        {formatTime(record.collected_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  )
}
