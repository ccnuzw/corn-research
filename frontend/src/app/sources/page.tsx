// 数据源管理页面
'use client'

import { useState, useEffect } from 'react'
import { AppLayout } from '@/components/layout/app-layout'
import { Breadcrumb } from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { 
  Database, 
  Plus, 
  RefreshCw, 
  Edit, 
  Trash2, 
  Globe,
  CheckCircle,
  XCircle,
  Search,
} from 'lucide-react'
import { api, type Source } from '@/lib/api'
import { toast } from 'sonner'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { SourceDialog } from '@/components/sources/source-dialog'

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingSource, setEditingSource] = useState<Source | null>(null)
  const confirm = useConfirm()

  const loadSources = async () => {
    try {
      setLoading(true)
      const response = await api.listSources()
      if (response.success && response.data) {
        setSources(response.data)
      } else {
        toast.error('加载数据源失败')
      }
    } catch (error) {
      console.error('Failed to load sources:', error)
      toast.error('加载数据源失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSources()
  }, [])

  const handleCreate = () => {
    setEditingSource(null)
    setDialogOpen(true)
  }

  const handleEdit = (source: Source) => {
    setEditingSource(source)
    setDialogOpen(true)
  }

  const handleDelete = async (source: Source) => {
    const ok = await confirm({
      title: '删除数据源',
      description: `确定要删除数据源"${source.name}"吗？此操作无法撤销。`,
      confirmText: '删除',
      destructive: true,
    })

    if (!ok) return

    try {
      const response = await api.deleteSource(source.id)
      if (response.success) {
        toast.success(`数据源"${source.name}"已删除`)
        await loadSources()
      } else {
        toast.error(response.message || '删除失败')
      }
    } catch (error) {
      console.error('Failed to delete source:', error)
      toast.error('删除失败')
    }
  }

  const handleToggleStatus = async (source: Source) => {
    const newStatus = source.status === 'active' ? 'inactive' : 'active'
    
    try {
      const response = await api.updateSource(source.id, { status: newStatus })
      if (response.success) {
        toast.success(`数据源已${newStatus === 'active' ? '启用' : '禁用'}`)
        await loadSources()
      } else {
        toast.error(response.message || '更新失败')
      }
    } catch (error) {
      console.error('Failed to update source:', error)
      toast.error('更新失败')
    }
  }

  const handleDialogClose = async (shouldRefresh: boolean) => {
    setDialogOpen(false)
    setEditingSource(null)
    if (shouldRefresh) {
      await loadSources()
    }
  }

  const filteredSources = sources.filter(source => {
    const query = searchQuery.toLowerCase()
    return (
      source.name.toLowerCase().includes(query) ||
      source.id.toLowerCase().includes(query) ||
      source.domain?.toLowerCase().includes(query) ||
      source.description?.toLowerCase().includes(query)
    )
  })

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (loading) {
    return (
      <AppLayout title="数据源管理">
        <div className="flex items-center justify-center h-96">
          <RefreshCw className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout title="数据源管理" subtitle="管理所有数据采集源">
      <div className="space-y-4">
        {/* 面包屑 */}
        <Breadcrumb
          items={[
            { label: '控制台', href: '/' },
            { label: '数据源管理', icon: <Database className="w-4 h-4" /> },
          ]}
        />

        {/* 工具栏 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* 搜索框 */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="搜索数据源..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-2 w-64 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <div className="text-sm text-muted-foreground">
              共 {sources.length} 个数据源
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadSources}>
              <RefreshCw className="w-4 h-4" />
              刷新
            </Button>
            <Button size="sm" onClick={handleCreate}>
              <Plus className="w-4 h-4" />
              新建数据源
            </Button>
          </div>
        </div>

        {/* 数据源列表 */}
        <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
          {filteredSources.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground">
              <Database className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>{searchQuery ? '没有找到匹配的数据源' : '暂无数据源'}</p>
              {!searchQuery && (
                <Button className="mt-4" onClick={handleCreate}>
                  <Plus className="w-4 h-4" />
                  新建数据源
                </Button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-muted/50">
                  <tr className="h-11">
                    <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                      数据源ID
                    </th>
                    <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                      名称
                    </th>
                    <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                      域名
                    </th>
                    <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                      描述
                    </th>
                    <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                      状态
                    </th>
                    <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                      创建时间
                    </th>
                    <th className="px-4 text-right text-[12px] font-medium text-muted-foreground">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSources.map((source) => (
                    <tr
                      key={source.id}
                      className="h-14 border-b border-border hover:bg-accent/50 transition-colors"
                    >
                      <td className="px-4 text-[13px] font-mono">
                        {source.id}
                      </td>
                      <td className="px-4 text-[13px] font-medium">
                        {source.name}
                      </td>
                      <td className="px-4 text-[13px]">
                        {source.domain ? (
                          <div className="flex items-center gap-1.5 text-muted-foreground">
                            <Globe className="w-3.5 h-3.5" />
                            {source.domain}
                          </div>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td className="px-4 text-[13px] text-muted-foreground max-w-xs truncate">
                        {source.description || '-'}
                      </td>
                      <td className="px-4">
                        <button
                          onClick={() => handleToggleStatus(source)}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors hover:opacity-80"
                          style={{
                            backgroundColor:
                              source.status === 'active'
                                ? 'hsl(var(--success) / 0.1)'
                                : 'hsl(var(--muted) / 0.5)',
                            color:
                              source.status === 'active'
                                ? 'hsl(var(--success))'
                                : 'hsl(var(--muted-foreground))',
                          }}
                        >
                          {source.status === 'active' ? (
                            <>
                              <CheckCircle className="w-3 h-3" />
                              已启用
                            </>
                          ) : (
                            <>
                              <XCircle className="w-3 h-3" />
                              已禁用
                            </>
                          )}
                        </button>
                      </td>
                      <td className="px-4 text-[13px] text-muted-foreground">
                        {formatDate(source.created_at)}
                      </td>
                      <td className="px-4">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleEdit(source)}
                            className="p-1.5 text-muted-foreground hover:text-foreground transition-colors"
                            title="编辑"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(source)}
                            className="p-1.5 text-muted-foreground hover:text-destructive transition-colors"
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
        </div>
      </div>

      {/* 新建/编辑对话框 */}
      <SourceDialog
        open={dialogOpen}
        source={editingSource}
        onClose={handleDialogClose}
      />
    </AppLayout>
  )
}
