// 采集器管理页面 - 展示完整表格组件
'use client'

import { useState } from 'react'
import { AppLayout } from '@/components/layout/app-layout'
import { Breadcrumb } from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Database, Plus, Play, Pause, Trash2, RefreshCw, Download, Settings } from 'lucide-react'

interface Collector {
  id: string
  name: string
  source: string
  status: 'running' | 'idle' | 'error'
  lastRun: string
  nextRun: string
  records: number
  successRate: number
}

const MOCK_COLLECTORS: Collector[] = [
  {
    id: '1',
    name: '博亚和讯-山东到车',
    source: 'boyar.cn',
    status: 'running',
    lastRun: '2分钟前',
    nextRun: '58分钟后',
    records: 1234,
    successRate: 98.5,
  },
  {
    id: '2',
    name: '新浪财经-北港周报',
    source: 'finance.sina.com.cn',
    status: 'idle',
    lastRun: '1小时前',
    nextRun: '23小时后',
    records: 567,
    successRate: 100,
  },
  {
    id: '3',
    name: 'DCE官网-期货行情',
    source: 'dce.com.cn',
    status: 'running',
    lastRun: '刚刚',
    nextRun: '5分钟后',
    records: 8901,
    successRate: 99.2,
  },
  {
    id: '4',
    name: '网易订阅-市场快讯',
    source: 'dy.163.com',
    status: 'error',
    lastRun: '30分钟前',
    nextRun: '-',
    records: 234,
    successRate: 85.3,
  },
]

export default function CollectorsPage() {
  const [selected, setSelected] = useState<string[]>([])

  const toggleSelect = (id: string) => {
    setSelected(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const toggleSelectAll = () => {
    setSelected(prev =>
      prev.length === MOCK_COLLECTORS.length ? [] : MOCK_COLLECTORS.map(c => c.id)
    )
  }

  return (
    <AppLayout title="采集器管理">
      <div className="space-y-4">
        {/* 面包屑 */}
        <Breadcrumb
          items={[
            { label: '控制台', href: '/' },
            { label: '采集器管理', icon: <Database className="w-4 h-4" /> },
          ]}
        />

        {/* 工具栏 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Button size="sm">
              <Plus className="w-4 h-4" />
              新建采集器
            </Button>
            <Button variant="outline" size="sm">
              <RefreshCw className="w-4 h-4" />
              刷新
            </Button>
            <Button variant="outline" size="sm">
              <Download className="w-4 h-4" />
              导出
            </Button>
          </div>

          <div className="text-[12px] text-muted-foreground">
            共 {MOCK_COLLECTORS.length} 个采集器
          </div>
        </div>

        {/* 表格 */}
        <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr className="h-11">
                <th className="w-12 px-4">
                  <Checkbox
                    checked={selected.length === MOCK_COLLECTORS.length}
                    onCheckedChange={toggleSelectAll}
                  />
                </th>
                <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                  采集器名称
                </th>
                <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                  数据源
                </th>
                <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                  状态
                </th>
                <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                  上次运行
                </th>
                <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                  下次运行
                </th>
                <th className="px-4 text-right text-[12px] font-medium text-muted-foreground">
                  采集量
                </th>
                <th className="px-4 text-right text-[12px] font-medium text-muted-foreground">
                  成功率
                </th>
                <th className="px-4 text-right text-[12px] font-medium text-muted-foreground">
                  操作
                </th>
              </tr>
            </thead>
            <tbody>
              {MOCK_COLLECTORS.map(collector => (
                <tr
                  key={collector.id}
                  className={`h-14 border-b border-border transition-colors ${
                    selected.includes(collector.id)
                      ? 'bg-accent/20'
                      : 'hover:bg-accent/50'
                  }`}
                >
                  <td className="px-4">
                    <Checkbox
                      checked={selected.includes(collector.id)}
                      onCheckedChange={() => toggleSelect(collector.id)}
                    />
                  </td>
                  <td className="px-4 text-[13px] font-medium">{collector.name}</td>
                  <td className="px-4 text-[13px] text-muted-foreground font-mono">
                    {collector.source}
                  </td>
                  <td className="px-4">
                    <Badge
                      variant={
                        collector.status === 'running'
                          ? 'success'
                          : collector.status === 'error'
                          ? 'destructive'
                          : 'secondary'
                      }
                      className="rounded-full"
                    >
                      {collector.status === 'running' && '运行中'}
                      {collector.status === 'idle' && '空闲'}
                      {collector.status === 'error' && '错误'}
                    </Badge>
                  </td>
                  <td className="px-4 text-[13px] text-muted-foreground">
                    {collector.lastRun}
                  </td>
                  <td className="px-4 text-[13px] text-muted-foreground">
                    {collector.nextRun}
                  </td>
                  <td className="px-4 text-right text-[13px] font-mono">
                    {collector.records.toLocaleString()}
                  </td>
                  <td className="px-4 text-right text-[13px] font-mono">
                    {collector.successRate}%
                  </td>
                  <td className="px-4">
                    <div className="flex items-center justify-end gap-3">
                      {collector.status === 'running' ? (
                        <button className="text-muted-foreground hover:text-foreground transition-colors">
                          <Pause className="w-4 h-4" />
                        </button>
                      ) : (
                        <button className="text-muted-foreground hover:text-foreground transition-colors">
                          <Play className="w-4 h-4" />
                        </button>
                      )}
                      <button className="text-muted-foreground hover:text-foreground transition-colors">
                        <Settings className="w-4 h-4" />
                      </button>
                      <button className="text-muted-foreground hover:text-destructive transition-colors">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* 悬浮工具栏 */}
        {selected.length > 0 && (
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
            <div className="bg-card border border-border/60 shadow-2xl rounded-xl px-4 py-2.5 flex items-center gap-3">
              <div className="bg-accent/20 text-accent-foreground px-2.5 py-1 rounded-md text-[12px] font-medium">
                已选 {selected.length} 项
              </div>
              <div className="w-px h-5 bg-border" />
              <Button variant="ghost" size="sm">
                <Play className="w-4 h-4" />
                批量启动
              </Button>
              <Button variant="ghost" size="sm">
                <Pause className="w-4 h-4" />
                批量停止
              </Button>
              <Button variant="destructive" size="sm">
                <Trash2 className="w-4 h-4" />
                批量删除
              </Button>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  )
}
