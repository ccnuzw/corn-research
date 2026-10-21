// 采集器管理页面 - 连接真实API
'use client'

import { useState, useEffect } from 'react'
import { AppLayout } from '@/components/layout/app-layout'
import { Breadcrumb } from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Database, Plus, Play, Pause, Trash2, RefreshCw, Download, Settings } from 'lucide-react'
import { api, type AdapterWithSource } from '@/lib/api'

export default function CollectorsPage() {
  const [adapters, setAdapters] = useState<AdapterWithSource[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadAdapters = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.listAdapters()
      if (response.success && response.data) {
        setAdapters(response.data)
      } else {
        setError(response.message || 'Failed to load adapters')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAdapters()
  }, [])

  const toggleSelect = (id: string) => {
    setSelected(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const toggleSelectAll = () => {
    setSelected(prev =>
      prev.length === adapters.length ? [] : adapters.map(a => a.adapter.id)
    )
  }

  const handleRun = async (id: string) => {
    try {
      const response = await api.runAdapter(id)
      if (response.success) {
        alert(`采集已启动: ${response.data?.message}`)
        loadAdapters()
      } else {
        alert(`启动失败: ${response.message}`)
      }
    } catch (err) {
      alert(`启动失败: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  const handleStart = async (id: string) => {
    try {
      const response = await api.startAdapter(id)
      if (response.success) {
        loadAdapters()
      }
    } catch (err) {
      alert(`操作失败: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  const handleStop = async (id: string) => {
    try {
      const response = await api.stopAdapter(id)
      if (response.success) {
        loadAdapters()
      }
    } catch (err) {
      alert(`操作失败: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('确定要删除这个采集器吗？')) return

    try {
      const response = await api.deleteAdapter(id)
      if (response.success) {
        loadAdapters()
      }
    } catch (err) {
      alert(`删除失败: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 1) return '刚刚'
    if (minutes < 60) return `${minutes}分钟前`
    if (hours < 24) return `${hours}小时前`
    return `${days}天前`
  }

  const getSuccessRate = (adapter: AdapterWithSource['adapter']) => {
    if (adapter.total_runs === 0) return 0
    return ((adapter.successful_runs / adapter.total_runs) * 100).toFixed(1)
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
            <Button size="sm" onClick={() => alert('创建功能开发中')}>
              <Plus className="w-4 h-4" />
              新建采集器
            </Button>
            <Button variant="outline" size="sm" onClick={loadAdapters} disabled={loading}>
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              刷新
            </Button>
            <Button variant="outline" size="sm" onClick={() => alert('导出功能开发中')}>
              <Download className="w-4 h-4" />
              导出
            </Button>
          </div>

          <div className="text-[12px] text-muted-foreground">
            共 {adapters.length} 个采集器
          </div>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {/* 加载中 */}
        {loading && adapters.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2" />
            加载中...
          </div>
        )}

        {/* 空状态 */}
        {!loading && adapters.length === 0 && !error && (
          <div className="text-center py-12 text-muted-foreground">
            <Database className="w-12 h-12 mx-auto mb-4 opacity-20" />
            <p>还没有采集器</p>
            <p className="text-xs mt-1">点击上方"新建采集器"按钮创建第一个采集器</p>
          </div>
        )}

        {/* 表格 */}
        {adapters.length > 0 && (
          <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
            <table className="w-full">
              <thead className="bg-muted/50">
                <tr className="h-11">
                  <th className="w-12 px-4">
                    <Checkbox
                      checked={selected.length === adapters.length}
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
                    主题
                  </th>
                  <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                    状态
                  </th>
                  <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                    上次运行
                  </th>
                  <th className="px-4 text-right text-[12px] font-medium text-muted-foreground">
                    运行次数
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
                {adapters.map(({ adapter, source }) => (
                  <tr
                    key={adapter.id}
                    className={`h-14 border-b border-border transition-colors ${
                      selected.includes(adapter.id)
                        ? 'bg-accent/20'
                        : 'hover:bg-accent/50'
                    }`}
                  >
                    <td className="px-4">
                      <Checkbox
                        checked={selected.includes(adapter.id)}
                        onCheckedChange={() => toggleSelect(adapter.id)}
                      />
                    </td>
                    <td className="px-4 text-[13px] font-medium">{adapter.name}</td>
                    <td className="px-4 text-[13px] text-muted-foreground">
                      {source?.name || adapter.source_id}
                    </td>
                    <td className="px-4 text-[13px] text-muted-foreground font-mono">
                      {adapter.topic_name}
                    </td>
                    <td className="px-4">
                      <Badge
                        variant={
                          adapter.status === 'running'
                            ? 'success'
                            : adapter.status === 'error'
                            ? 'destructive'
                            : 'secondary'
                        }
                        className="rounded-full"
                      >
                        {adapter.status === 'running' && '运行中'}
                        {adapter.status === 'stopped' && '已停止'}
                        {adapter.status === 'error' && '错误'}
                      </Badge>
                    </td>
                    <td className="px-4 text-[13px] text-muted-foreground">
                      {formatDate(adapter.last_run_at)}
                    </td>
                    <td className="px-4 text-right text-[13px] font-mono">
                      {adapter.total_runs}
                    </td>
                    <td className="px-4 text-right text-[13px] font-mono">
                      {getSuccessRate(adapter)}%
                    </td>
                    <td className="px-4">
                      <div className="flex items-center justify-end gap-3">
                        <button 
                          className="text-muted-foreground hover:text-foreground transition-colors"
                          onClick={() => handleRun(adapter.id)}
                          title="手动运行"
                        >
                          <Play className="w-4 h-4" />
                        </button>
                        {adapter.status === 'running' ? (
                          <button 
                            className="text-muted-foreground hover:text-foreground transition-colors"
                            onClick={() => handleStop(adapter.id)}
                            title="停止"
                          >
                            <Pause className="w-4 h-4" />
                          </button>
                        ) : (
                          <button 
                            className="text-muted-foreground hover:text-foreground transition-colors"
                            onClick={() => handleStart(adapter.id)}
                            title="启动"
                          >
                            <Play className="w-4 h-4" />
                          </button>
                        )}
                        <button 
                          className="text-muted-foreground hover:text-foreground transition-colors"
                          onClick={() => alert('配置功能开发中')}
                          title="配置"
                        >
                          <Settings className="w-4 h-4" />
                        </button>
                        <button 
                          className="text-muted-foreground hover:text-destructive transition-colors"
                          onClick={() => handleDelete(adapter.id)}
                          title="删除"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 悬浮工具栏 */}
        {selected.length > 0 && (
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
            <div className="bg-card border border-border/60 shadow-2xl rounded-xl px-4 py-2.5 flex items-center gap-3">
              <div className="bg-accent/20 text-accent-foreground px-2.5 py-1 rounded-md text-[12px] font-medium">
                已选 {selected.length} 项
              </div>
              <div className="w-px h-5 bg-border" />
              <Button variant="ghost" size="sm" onClick={() => alert('批量启动功能开发中')}>
                <Play className="w-4 h-4" />
                批量启动
              </Button>
              <Button variant="ghost" size="sm" onClick={() => alert('批量停止功能开发中')}>
                <Pause className="w-4 h-4" />
                批量停止
              </Button>
              <Button 
                variant="destructive" 
                size="sm"
                onClick={() => {
                  if (confirm(`确定要删除选中的 ${selected.length} 个采集器吗？`)) {
                    alert('批量删除功能开发中')
                  }
                }}
              >
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
