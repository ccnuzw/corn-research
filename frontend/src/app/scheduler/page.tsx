// 定时任务管理页面
'use client'

import { useState, useEffect } from 'react'
import { AppLayout } from '@/components/layout/app-layout'
import { Breadcrumb } from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Clock, Plus, Play, Edit, Trash2, Calendar } from 'lucide-react'
import { api, type ScheduledJob } from '@/lib/api'

interface Collector {
  id: string
  name: string
}

// Cron表达式预设
const CRON_PRESETS = [
  { label: '每天 8:00', value: '0 0 8 * * *' },
  { label: '每天 12:00', value: '0 0 12 * * *' },
  { label: '每天 18:00', value: '0 0 18 * * *' },
  { label: '每小时', value: '0 0 * * * *' },
  { label: '每30分钟', value: '0 */30 * * * *' },
  { label: '每周一 9:00', value: '0 0 9 * * 1' },
  { label: '自定义', value: 'custom' },
]

const COLLECTORS: Collector[] = [
  { id: 'boyar', name: '博亚和讯' },
  { id: 'sina', name: '新浪财经' },
  { id: 'dce', name: 'DCE官网' },
  { id: 'netease', name: '网易订阅' },
]

export default function SchedulerPage() {
  const [jobs, setJobs] = useState<ScheduledJob[]>([])
  const [loading, setLoading] = useState(true)
  const [showDialog, setShowDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [selectedJob, setSelectedJob] = useState<string | null>(null)
  
  // 表单状态
  const [formData, setFormData] = useState({
    name: '',
    collector_id: '',
    cron_expression: '0 0 8 * * *',
    description: '',
    enabled: true,
  })
  const [cronPreset, setCronPreset] = useState('0 0 8 * * *')

  // 加载任务列表
  const loadJobs = async () => {
    try {
      const data = await api.getJobs()
      setJobs(data || [])
    } catch (error) {
      console.error('Failed to load jobs:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadJobs()
    const interval = setInterval(loadJobs, 30000) // 每30秒刷新
    return () => clearInterval(interval)
  }, [])

  // 创建任务
  const handleCreateJob = async () => {
    try {
      await api.createJob({
        name: formData.name,
        collector_id: formData.collector_id,
        cron_expression: formData.cron_expression,
        description: formData.description,
        enabled: formData.enabled,
      })
      setShowDialog(false)
      loadJobs()
      // 重置表单
      setFormData({
        name: '',
        collector_id: '',
        cron_expression: '0 0 8 * * *',
        description: '',
        enabled: true,
      })
      setCronPreset('0 0 8 * * *')
    } catch (error) {
      console.error('Failed to create job:', error)
      alert('创建失败')
    }
  }

  // 删除任务
  const handleDeleteJob = async () => {
    if (!selectedJob) return
    try {
      await api.deleteJob(selectedJob)
      setShowDeleteDialog(false)
      setSelectedJob(null)
      loadJobs()
    } catch (error) {
      console.error('Failed to delete job:', error)
      alert('删除失败')
    }
  }

  // 切换任务启用状态
  const handleToggleJob = async (jobId: string, enabled: boolean) => {
    try {
      await api.toggleJob(jobId, enabled)
      loadJobs()
    } catch (error) {
      console.error('Failed to toggle job:', error)
      alert('操作失败')
    }
  }

  // 手动触发任务
  const handleTriggerJob = async (jobId: string) => {
    try {
      await api.triggerJob(jobId)
      alert('任务已触发')
      loadJobs()
    } catch (error) {
      console.error('Failed to trigger job:', error)
      alert('触发失败')
    }
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString('zh-CN')
  }

  const getSuccessRate = (job: ScheduledJob) => {
    if (job.total_runs === 0) return '-'
    return `${((job.success_count / job.total_runs) * 100).toFixed(1)}%`
  }

  return (
    <AppLayout title="定时任务管理">
      <div className="space-y-4">
        {/* 面包屑 */}
        <Breadcrumb
          items={[
            { label: '控制台', href: '/' },
            { label: '定时任务管理', icon: <Clock className="w-4 h-4" /> },
          ]}
        />

        {/* 工具栏 */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-card-foreground">定时任务</h2>
            <p className="text-sm text-muted-foreground">共 {jobs.length} 个任务</p>
          </div>
          <Button size="sm" onClick={() => setShowDialog(true)}>
            <Plus className="w-4 h-4" />
            新建任务
          </Button>
        </div>

        {/* 任务列表 */}
        <div className="bg-card rounded-lg border border-border">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted/30">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">
                    任务名称
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">
                    采集器
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">
                    Cron表达式
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">
                    状态
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">
                    上次运行
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">
                    成功率
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-card divide-y divide-border">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-sm text-muted-foreground">
                      加载中...
                    </td>
                  </tr>
                ) : jobs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-sm text-muted-foreground">
                      暂无定时任务
                    </td>
                  </tr>
                ) : (
                  jobs.map((job) => (
                    <tr key={job.id} className="hover:bg-muted/30">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-card-foreground">{job.name}</div>
                        {job.description && (
                          <div className="text-xs text-muted-foreground">{job.description}</div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-card-foreground">
                          {job.collector_id ? (
                            COLLECTORS.find(c => c.id === job.collector_id)?.name || job.collector_id
                          ) : (
                            <span className="text-gray-400">多采集器</span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <code className="text-xs bg-muted px-2 py-1 rounded">
                          {job.cron_expression}
                        </code>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={job.enabled}
                            onCheckedChange={(checked) => handleToggleJob(job.id, checked)}
                          />
                          <Badge variant={job.enabled ? 'default' : 'secondary'}>
                            {job.enabled ? '启用' : '禁用'}
                          </Badge>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-card-foreground">{formatDate(job.last_run)}</div>
                        <div className="text-xs text-muted-foreground">
                          运行 {job.total_runs} 次
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-card-foreground">{getSuccessRate(job)}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleTriggerJob(job.id)}
                          >
                            <Play className="w-3 h-3" />
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setSelectedJob(job.id)
                              setShowDeleteDialog(true)
                            }}
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 创建任务对话框 */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>新建定时任务</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">任务名称</Label>
              <Input
                id="name"
                placeholder="例如：每日采集博亚数据"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="collector">采集器</Label>
              <Select
                value={formData.collector_id}
                onValueChange={(value) => setFormData({ ...formData, collector_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择采集器" />
                </SelectTrigger>
                <SelectContent>
                  {COLLECTORS.map((collector) => (
                    <SelectItem key={collector.id} value={collector.id}>
                      {collector.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="cron-preset">执行时间</Label>
              <Select
                value={cronPreset}
                onValueChange={(value) => {
                  setCronPreset(value)
                  if (value !== 'custom') {
                    setFormData({ ...formData, cron_expression: value })
                  }
                }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CRON_PRESETS.map((preset) => (
                    <SelectItem key={preset.value} value={preset.value}>
                      {preset.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {cronPreset === 'custom' && (
              <div className="space-y-2">
                <Label htmlFor="cron">Cron表达式</Label>
                <Input
                  id="cron"
                  placeholder="0 0 8 * * *"
                  value={formData.cron_expression}
                  onChange={(e) => setFormData({ ...formData, cron_expression: e.target.value })}
                />
                <p className="text-xs text-muted-foreground">
                  格式：秒 分 时 日 月 周（例如：0 0 8 * * * = 每天8:00）
                </p>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="description">描述（可选）</Label>
              <Textarea
                id="description"
                placeholder="任务描述"
                rows={3}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="enabled"
                checked={formData.enabled}
                onCheckedChange={(checked) => setFormData({ ...formData, enabled: checked })}
              />
              <Label htmlFor="enabled">创建后立即启用</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDialog(false)}>
              取消
            </Button>
            <Button 
              onClick={handleCreateJob}
              disabled={!formData.name || !formData.collector_id || !formData.cron_expression}
            >
              创建任务
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 删除确认对话框 */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-muted-foreground">
              确定要删除这个定时任务吗？此操作无法撤销。
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDeleteJob}>
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  )
}
