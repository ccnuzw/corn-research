// 数据源新建/编辑对话框
'use client'

import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { api, type Source } from '@/lib/api'
import { toast } from 'sonner'
import { RefreshCw } from 'lucide-react'

interface SourceDialogProps {
  open: boolean
  source: Source | null
  onClose: (shouldRefresh: boolean) => void
}

export function SourceDialog({ open, source, onClose }: SourceDialogProps) {
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    domain: '',
    description: '',
    status: 'active',
  })
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (source) {
      setFormData({
        id: source.id,
        name: source.name,
        domain: source.domain || '',
        description: source.description || '',
        status: source.status,
      })
    } else {
      setFormData({
        id: '',
        name: '',
        domain: '',
        description: '',
        status: 'active',
      })
    }
    setErrors({})
  }, [source, open])

  const validateForm = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.id.trim()) {
      newErrors.id = '数据源ID不能为空'
    } else if (!/^[a-z0-9_-]+$/.test(formData.id)) {
      newErrors.id = '只能包含小写字母、数字、下划线和连字符'
    }

    if (!formData.name.trim()) {
      newErrors.name = '数据源名称不能为空'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) return

    setLoading(true)
    try {
      const payload = {
        name: formData.name.trim(),
        domain: formData.domain.trim() || null,
        description: formData.description.trim() || null,
        status: formData.status,
      }

      let response
      if (source) {
        // 编辑
        response = await api.updateSource(source.id, payload)
      } else {
        // 新建
        response = await api.createSource({
          id: formData.id.trim(),
          ...payload,
        })
      }

      if (response.success) {
        toast.success(source ? '数据源已更新' : '数据源已创建')
        onClose(true)
      } else {
        toast.error(response.message || '操作失败')
      }
    } catch (error) {
      console.error('Failed to save source:', error)
      toast.error('操作失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = () => {
    onClose(false)
  }

  return (
    <Dialog open={open} onOpenChange={(open) => !open && handleCancel()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{source ? '编辑数据源' : '新建数据源'}</DialogTitle>
          <DialogDescription>
            {source ? '修改数据源配置信息' : '添加新的数据采集源'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
          {/* 数据源ID */}
          <div className="space-y-2">
            <Label htmlFor="id">
              数据源ID <span className="text-destructive">*</span>
            </Label>
            <Input
              id="id"
              value={formData.id}
              onChange={(e) => setFormData({ ...formData, id: e.target.value })}
              placeholder="例如: sina, boyar"
              disabled={!!source || loading}
              className={errors.id ? 'border-destructive' : ''}
            />
            {errors.id && (
              <p className="text-xs text-destructive">{errors.id}</p>
            )}
            {!source && (
              <p className="text-xs text-muted-foreground">
                只能包含小写字母、数字、下划线和连字符，创建后不可修改
              </p>
            )}
          </div>

          {/* 数据源名称 */}
          <div className="space-y-2">
            <Label htmlFor="name">
              数据源名称 <span className="text-destructive">*</span>
            </Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="例如: 新浪财经"
              disabled={loading}
              className={errors.name ? 'border-destructive' : ''}
            />
            {errors.name && (
              <p className="text-xs text-destructive">{errors.name}</p>
            )}
          </div>

          {/* 域名 */}
          <div className="space-y-2">
            <Label htmlFor="domain">域名</Label>
            <Input
              id="domain"
              value={formData.domain}
              onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
              placeholder="例如: sina.com.cn"
              disabled={loading}
            />
            <p className="text-xs text-muted-foreground">
              数据源网站的域名（可选）
            </p>
          </div>

          {/* 描述 */}
          <div className="space-y-2">
            <Label htmlFor="description">描述</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="数据源的详细描述..."
              disabled={loading}
              rows={3}
            />
          </div>

          {/* 状态 */}
          <div className="space-y-2">
            <Label htmlFor="status">状态</Label>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="status"
                  value="active"
                  checked={formData.status === 'active'}
                  onChange={(e) => setFormData({ ...formData, status: 'active' })}
                  disabled={loading}
                  className="w-4 h-4"
                />
                <span className="text-sm">启用</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="status"
                  value="inactive"
                  checked={formData.status === 'inactive'}
                  onChange={(e) => setFormData({ ...formData, status: 'inactive' })}
                  disabled={loading}
                  className="w-4 h-4"
                />
                <span className="text-sm">禁用</span>
              </label>
            </div>
          </div>

          {/* 按钮 */}
          <div className="flex justify-end gap-2 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={handleCancel}
              disabled={loading}
            >
              取消
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  保存中...
                </>
              ) : (
                <>保存</>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
