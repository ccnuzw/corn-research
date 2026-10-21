// 定时任务管理页面
'use client'

import { useState, useEffect } from 'react'
import { AppLayout } from '@/components/layout/app-layout'
import { Breadcrumb } from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Clock, Plus, Play, Pause, Trash2, RefreshCw } from 'lucide-react'

interface Job {
  id: string
  name: string
  collector_id: string
  cron_expression: string
  enabled: boolean
  next_run: string | null
  last_run: string | null
  status: 'running' | 'waiting' | 'stopped'
}

const MOCK_JOBS: Job[] = [
  {
    id: '1',
    name: '每日早8点采集',
    collector_id: 'boyar_production',
    cron_expression: '0 8 * * *',
    enabled: true,
    next_run: '明天 08:00',
    last_run: '今天 08:00',
    status: 'waiting',
  },
  {
    id: '2',
    name: '每小时采集',
    collector_id: 'sina_production',
    cron_expression: '0 * * * *',
    enabled: true,
    next_run: '12分钟后',
    last_run: '48分钟前',
    status: 'waiting',
  },
  {
    id: '3',
    name: '每周一采集',
    collector_id: 'dce',
    cron_expression: '0 9 * * 1',
    enabled: false,
    next_run: null,
    last_run: '上周一 09:00',
    status: 'stopped',
  },
]

export default function SchedulerPage() {
  const [jobs, setJobs] = useState<Job[]>(MOCK_JOBS)
  const [loading, setLoading] = useState(false)

  const parseCronExpression = (cron: string) => {
    // 简单的 cron 表达式解析
    const parts = cron.split(' ')
    if (parts.length !== 5) return cron
    
    const [minute, hour, day, month, weekday] = parts
    
    if (minute === '0' && hour !== '*' && day === '*' && month === '*' && weekday === '*') {
      return `每天 ${hour.padStart(2, '0')}:00`
    }
    if (minute === '0' && hour === '*') {
      return '每小时'
    }
    if (weekday !== '*') {
      const days = ['日', '一', '二', '三', '四', '五', '六']
      return `每周${days[parseInt(weekday)]} ${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`
    }
    return cron
  }

  return (
    <AppLayout title="定时任务">
      <div className="space-y-4">
        {/* 面包屑 */}
        <Breadcrumb
          items={[
            { label: '控制台', href: '/' },
            { label: '定时任务', icon: <Clock className="w-4 h-4" /> },
          ]}
        />

        {/* 工具栏 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={() => alert('创建功能开发中')}>
              <Plus className="w-4 h-4" />
              新建任务
            </Button>
            <Button variant="outline" size="sm" disabled={loading}>
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              刷新
            </Button>
          </div>

          <div className="text-[12px] text-muted-foreground">
            共 {jobs.length} 个定时任务，{jobs.filter(j => j.enabled).length} 个启用
          </div>
        </div>

        {/* 任务列表 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {jobs.map((job) => (
            <div
              key={job.id}
              className="rounded-lg border border-border/60 bg-card p-4 hover:shadow-lg transition-all"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-sm">{job.name}</h3>
                  <p className="text-xs text-muted-foreground mt-0.5 font-mono">
                    {job.collector_id}
                  </p>
                </div>
                <Badge
                  variant={
                    job.status === 'running'
                      ? 'default'
                      : job.status === 'stopped'
                      ? 'secondary'
                      : 'outline'
                  }
                  className="rounded-full"
                >
                  {job.status === 'running' && '运行中'}
                  {job.status === 'waiting' && '等待中'}
                  {job.status === 'stopped' && '已停止'}
                </Badge>
              </div>

              <div className="space-y-2 mb-4">
                <div className="flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">
                    {parseCronExpression(job.cron_expression)}
                  </span>
                </div>
                {job.next_run && (
                  <div className="text-xs">
                    <span className="text-muted-foreground">下次运行: </span>
                    <span className="font-medium">{job.next_run}</span>
                  </div>
                )}
                {job.last_run && (
                  <div className="text-xs">
                    <span className="text-muted-foreground">上次运行: </span>
                    <span>{job.last_run}</span>
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2">
                {job.enabled ? (
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => alert('暂停功能开发中')}
                  >
                    <Pause className="w-3.5 h-3.5" />
                    暂停
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => alert('启动功能开发中')}
                  >
                    <Play className="w-3.5 h-3.5" />
                    启动
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => alert('立即运行功能开发中')}
                >
                  <Play className="w-3.5 h-3.5" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => alert('删除功能开发中')}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          ))}
        </div>

        {jobs.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <Clock className="w-12 h-12 mx-auto mb-4 opacity-20" />
            <p>还没有定时任务</p>
            <p className="text-xs mt-1">点击上方"新建任务"按钮创建第一个任务</p>
          </div>
        )}
      </div>
    </AppLayout>
  )
}
