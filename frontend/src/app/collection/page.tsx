'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Plus, Play, Square, Trash2, RefreshCw, Edit, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';

// API Base URL
const API_BASE = 'http://localhost:18000';

interface Source {
  id: string;
  name: string;
  domain: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface Adapter {
  id: string;
  name: string;
  script_file: string;
  source_id: string;
  topic_name: string;
  status: string;
  last_run_at?: string;
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
}

interface Topic {
  name: string;
  adapter_count: number;
  record_count: number;
}

interface AdapterFormData {
  name: string;
  script_file: string;
  source_id: string;
  topic_name: string;
}

export default function CollectionPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('sources');
  const [sources, setSources] = useState<Source[]>([]);
  const [adapters, setAdapters] = useState<Adapter[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(true);

  // Dialog states
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedAdapter, setSelectedAdapter] = useState<Adapter | null>(null);

  // Form states
  const [formData, setFormData] = useState<AdapterFormData>({
    name: '',
    script_file: '',
    source_id: '',
    topic_name: '',
  });
  const [formErrors, setFormErrors] = useState<Partial<AdapterFormData>>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [sourcesRes, adaptersRes, topicsRes] = await Promise.all([
        fetch(`${API_BASE}/api/sources`),
        fetch(`${API_BASE}/api/adapters`),
        fetch(`${API_BASE}/api/topics`),
      ]);

      const sourcesData = await sourcesRes.json();
      const adaptersData = await adaptersRes.json();
      const topicsData = await topicsRes.json();

      if (sourcesData.success) setSources(sourcesData.data || []);
      if (adaptersData.success) setAdapters(adaptersData.data || []);
      if (topicsData.success) setTopics(topicsData.data || []);
    } catch (error) {
      console.error('Failed to load data:', error);
      toast.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const validateForm = (data: AdapterFormData): boolean => {
    const errors: Partial<AdapterFormData> = {};

    if (!data.name.trim()) errors.name = '请输入适配器名称';
    if (!data.script_file.trim()) errors.script_file = '请输入脚本文件路径';
    if (!data.source_id) errors.source_id = '请选择数据源';
    if (!data.topic_name.trim()) errors.topic_name = '请输入数据主题';

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleCreateAdapter = async () => {
    if (!validateForm(formData)) return;

    setSubmitting(true);
    try {
      const response = await fetch(`${API_BASE}/api/adapters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      const result = await response.json();

      if (result.success) {
        toast.success('适配器创建成功');
        setCreateDialogOpen(false);
        resetForm();
        await loadData();
      } else {
        toast.error(result.message || '创建失败');
      }
    } catch (error) {
      console.error('Failed to create adapter:', error);
      toast.error('创建适配器失败');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEditAdapter = async () => {
    if (!selectedAdapter || !validateForm(formData)) return;

    setSubmitting(true);
    try {
      const response = await fetch(`${API_BASE}/api/adapters/${selectedAdapter.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      const result = await response.json();

      if (result.success) {
        toast.success('适配器更新成功');
        setEditDialogOpen(false);
        setSelectedAdapter(null);
        resetForm();
        await loadData();
      } else {
        toast.error(result.message || '更新失败');
      }
    } catch (error) {
      console.error('Failed to update adapter:', error);
      toast.error('更新适配器失败');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteAdapter = async () => {
    if (!selectedAdapter) return;

    setSubmitting(true);
    try {
      const response = await fetch(`${API_BASE}/api/adapters/${selectedAdapter.id}`, {
        method: 'DELETE',
      });

      const result = await response.json();

      if (result.success) {
        toast.success('适配器删除成功');
        setDeleteDialogOpen(false);
        setSelectedAdapter(null);
        await loadData();
      } else {
        toast.error(result.message || '删除失败');
      }
    } catch (error) {
      console.error('Failed to delete adapter:', error);
      toast.error('删除适配器失败');
    } finally {
      setSubmitting(false);
    }
  };

  const handleStartStop = async (adapter: Adapter) => {
    const action = adapter.status === 'running' ? 'stop' : 'start';
    try {
      const response = await fetch(`${API_BASE}/api/adapters/${adapter.id}/${action}`, {
        method: 'POST',
      });

      const result = await response.json();

      if (result.success) {
        toast.success(action === 'start' ? '采集已启动' : '采集已停止');
        await loadData();
      } else {
        toast.error(result.message || `${action === 'start' ? '启动' : '停止'}失败`);
      }
    } catch (error) {
      console.error(`Failed to ${action} adapter:`, error);
      toast.error(`${action === 'start' ? '启动' : '停止'}采集失败`);
    }
  };

  const openCreateDialog = () => {
    resetForm();
    setCreateDialogOpen(true);
  };

  const openEditDialog = (adapter: Adapter) => {
    setSelectedAdapter(adapter);
    setFormData({
      name: adapter.name,
      script_file: adapter.script_file,
      source_id: adapter.source_id,
      topic_name: adapter.topic_name,
    });
    setFormErrors({});
    setEditDialogOpen(true);
  };

  const openDeleteDialog = (adapter: Adapter) => {
    setSelectedAdapter(adapter);
    setDeleteDialogOpen(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      script_file: '',
      source_id: '',
      topic_name: '',
    });
    setFormErrors({});
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, { label: string; className: string }> = {
      running: { label: '运行中', className: 'bg-green-500' },
      stopped: { label: '已停止', className: 'bg-gray-500' },
      error: { label: '错误', className: 'bg-red-500' },
      active: { label: '活跃', className: 'bg-blue-500' },
      inactive: { label: '未激活', className: 'bg-gray-400' },
    };
    const variant = variants[status] || variants.stopped;
    return <Badge className={variant.className}>{variant.label}</Badge>;
  };

  const getSourceName = (sourceId: string) => {
    return sources.find((s) => s.id === sourceId)?.name || sourceId;
  };

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-96">
        <div className="text-muted-foreground">加载中...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">采集管理</h1>
          <p className="text-muted-foreground mt-1">管理数据源、采集适配器和数据主题</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadData} className="gap-2">
            <RefreshCw className="w-4 h-4" />刷新
          </Button>
          <Button onClick={openCreateDialog} className="gap-2">
            <Plus className="w-4 h-4" />新建适配器
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full max-w-md grid-cols-3">
          <TabsTrigger value="sources">数据源</TabsTrigger>
          <TabsTrigger value="adapters">适配器</TabsTrigger>
          <TabsTrigger value="topics">数据主题</TabsTrigger>
        </TabsList>

        <TabsContent value="sources" className="space-y-4">
          <Card className="p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">数据源列表</h2>
                <span className="text-sm text-muted-foreground">共 {sources.length} 个数据源</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-3 font-medium">名称</th>
                      <th className="pb-3 font-medium">域名</th>
                      <th className="pb-3 font-medium">描述</th>
                      <th className="pb-3 font-medium">状态</th>
                      <th className="pb-3 font-medium">创建时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sources.map((source) => (
                      <tr key={source.id} className="border-b hover:bg-muted/50">
                        <td className="py-4 font-medium">{source.name}</td>
                        <td className="py-4 text-sm text-muted-foreground">{source.domain}</td>
                        <td className="py-4 text-sm">{source.description}</td>
                        <td className="py-4">{getStatusBadge(source.status)}</td>
                        <td className="py-4 text-sm text-muted-foreground">
                          {new Date(source.created_at).toLocaleDateString('zh-CN')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="adapters" className="space-y-4">
          <Card className="p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">适配器列表</h2>
                <span className="text-sm text-muted-foreground">共 {adapters.length} 个适配器</span>
              </div>
              {adapters.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  暂无适配器，点击&ldquo;新建适配器&rdquo;创建
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="pb-3 font-medium">名称</th>
                        <th className="pb-3 font-medium">数据源</th>
                        <th className="pb-3 font-medium">主题</th>
                        <th className="pb-3 font-medium">状态</th>
                        <th className="pb-3 font-medium">运行统计</th>
                        <th className="pb-3 font-medium">最后运行</th>
                        <th className="pb-3 font-medium text-right">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {adapters.map((adapter) => (
                        <tr key={adapter.id} className="border-b hover:bg-muted/50">
                          <td className="py-4">
                            <button
                              onClick={() => router.push(`/collection/${adapter.id}`)}
                              className="font-medium text-primary hover:underline flex items-center gap-1"
                            >
                              {adapter.name}
                              <ExternalLink className="w-3 h-3" />
                            </button>
                          </td>
                          <td className="py-4 text-sm">{getSourceName(adapter.source_id)}</td>
                          <td className="py-4 text-sm">{adapter.topic_name}</td>
                          <td className="py-4">{getStatusBadge(adapter.status)}</td>
                          <td className="py-4 text-sm">
                            <div className="flex gap-2">
                              <span className="text-green-600">{adapter.successful_runs}</span>
                              <span className="text-muted-foreground">/</span>
                              <span className="text-red-600">{adapter.failed_runs}</span>
                              <span className="text-muted-foreground">/</span>
                              <span>{adapter.total_runs}</span>
                            </div>
                          </td>
                          <td className="py-4 text-sm text-muted-foreground">
                            {adapter.last_run_at
                              ? new Date(adapter.last_run_at).toLocaleString('zh-CN')
                              : '未运行'}
                          </td>
                          <td className="py-4">
                            <div className="flex justify-end gap-2">
                              <Button
                                size="sm"
                                variant={adapter.status === 'running' ? 'destructive' : 'default'}
                                onClick={() => handleStartStop(adapter)}
                                className="gap-1"
                              >
                                {adapter.status === 'running' ? (
                                  <>
                                    <Square className="w-3 h-3" />
                                    停止
                                  </>
                                ) : (
                                  <>
                                    <Play className="w-3 h-3" />
                                    启动
                                  </>
                                )}
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => openEditDialog(adapter)}
                              >
                                <Edit className="w-3 h-3" />
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => openDeleteDialog(adapter)}
                              >
                                <Trash2 className="w-3 h-3" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="topics" className="space-y-4">
          <Card className="p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">数据主题列表</h2>
                <span className="text-sm text-muted-foreground">共 {topics.length} 个主题</span>
              </div>
              {topics.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">暂无数据主题</div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {topics.map((topic) => (
                    <Card key={topic.name} className="p-4">
                      <h3 className="font-semibold text-lg mb-2">{topic.name}</h3>
                      <div className="space-y-1 text-sm text-muted-foreground">
                        <div>适配器数: {topic.adapter_count}</div>
                        <div>记录数: {topic.record_count.toLocaleString()}</div>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Create Adapter Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建适配器</DialogTitle>
            <DialogDescription>配置数据采集适配器的基本信息</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">适配器名称 *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入适配器名称"
              />
              {formErrors.name && (
                <p className="text-sm text-red-500">{formErrors.name}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="script_file">脚本文件 *</Label>
              <Input
                id="script_file"
                value={formData.script_file}
                onChange={(e) => setFormData({ ...formData, script_file: e.target.value })}
                placeholder="例如: scrapers/usda_corn.py"
              />
              {formErrors.script_file && (
                <p className="text-sm text-red-500">{formErrors.script_file}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="source_id">数据源 *</Label>
              <Select
                value={formData.source_id}
                onValueChange={(value) => setFormData({ ...formData, source_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择数据源" />
                </SelectTrigger>
                <SelectContent>
                  {sources.map((source) => (
                    <SelectItem key={source.id} value={source.id}>
                      {source.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {formErrors.source_id && (
                <p className="text-sm text-red-500">{formErrors.source_id}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="topic_name">数据主题 *</Label>
              <Input
                id="topic_name"
                value={formData.topic_name}
                onChange={(e) => setFormData({ ...formData, topic_name: e.target.value })}
                placeholder="例如: corn_prices"
              />
              {formErrors.topic_name && (
                <p className="text-sm text-red-500">{formErrors.topic_name}</p>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreateAdapter} disabled={submitting}>
              {submitting ? '创建中...' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Adapter Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>编辑适配器</DialogTitle>
            <DialogDescription>修改适配器配置信息</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">适配器名称 *</Label>
              <Input
                id="edit-name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入适配器名称"
              />
              {formErrors.name && (
                <p className="text-sm text-red-500">{formErrors.name}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-script_file">脚本文件 *</Label>
              <Input
                id="edit-script_file"
                value={formData.script_file}
                onChange={(e) => setFormData({ ...formData, script_file: e.target.value })}
                placeholder="例如: scrapers/usda_corn.py"
              />
              {formErrors.script_file && (
                <p className="text-sm text-red-500">{formErrors.script_file}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-source_id">数据源 *</Label>
              <Select
                value={formData.source_id}
                onValueChange={(value) => setFormData({ ...formData, source_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择数据源" />
                </SelectTrigger>
                <SelectContent>
                  {sources.map((source) => (
                    <SelectItem key={source.id} value={source.id}>
                      {source.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {formErrors.source_id && (
                <p className="text-sm text-red-500">{formErrors.source_id}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-topic_name">数据主题 *</Label>
              <Input
                id="edit-topic_name"
                value={formData.topic_name}
                onChange={(e) => setFormData({ ...formData, topic_name: e.target.value })}
                placeholder="例如: corn_prices"
              />
              {formErrors.topic_name && (
                <p className="text-sm text-red-500">{formErrors.topic_name}</p>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleEditAdapter} disabled={submitting}>
              {submitting ? '保存中...' : '保存'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除适配器 <strong>{selectedAdapter?.name}</strong> 吗？此操作无法撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setSelectedAdapter(null)}>
              取消
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteAdapter}
              disabled={submitting}
              className="bg-red-600 hover:bg-red-700"
            >
              {submitting ? '删除中...' : '删除'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
