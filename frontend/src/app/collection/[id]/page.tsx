'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArrowLeft, Play, Square, RefreshCw, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { api, type Adapter, type Source, type CollectionRun, type CollectionRecord } from '@/lib/api';

export default function AdapterDetailPage() {
  const router = useRouter();
  const params = useParams();
  const adapterId = params.id as string;

  const [adapter, setAdapter] = useState<Adapter | null>(null);
  const [source, setSource] = useState<Source | null>(null);
  const [runHistory, setRunHistory] = useState<CollectionRun[]>([]);
  const [collectedData, setCollectedData] = useState<CollectionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('info');

  const loadAdapterDetails = useCallback(async () => {
    setLoading(true);
    try {
      const [adapterData, historyData, recordsData] = await Promise.all([
        api.getAdapter(adapterId),
        api.getAdapterRuns(adapterId),
        api.getAdapterRecords(adapterId, 50),
      ]);

      if (adapterData.success && adapterData.data) {
        if (!historyData.success) throw new Error(historyData.message || '加载运行历史失败');
        if (!recordsData.success) throw new Error(recordsData.message || '加载采集数据失败');
        setAdapter(adapterData.data);
        setSource(adapterData.data.source);
        setRunHistory(historyData.data || []);
        setCollectedData(recordsData.data || []);
      } else {
        toast.error('适配器不存在');
        router.push('/collection');
      }
    } catch (error) {
      console.error('Failed to load adapter details:', error);
      toast.error('加载详情失败');
    } finally {
      setLoading(false);
    }
  }, [adapterId, router]);

  useEffect(() => {
    loadAdapterDetails();
  }, [loadAdapterDetails]);

  const handleStartStop = async () => {
    if (!adapter) return;

    const action = adapter.status === 'running' ? 'stop' : 'start';
    try {
      const result = action === 'stop'
        ? await api.stopAdapter(adapterId)
        : await api.startAdapter(adapterId);

      if (result.success) {
        toast.success(action === 'start' ? '采集已启动' : '采集已停止');
        await loadAdapterDetails();
      } else {
        toast.error(result.message || `${action === 'start' ? '启动' : '停止'}失败`);
      }
    } catch (error) {
      console.error(`Failed to ${action} adapter:`, error);
      toast.error(`${action === 'start' ? '启动' : '停止'}采集失败`);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, { label: string; className: string }> = {
      running: { label: '运行中', className: 'bg-green-500' },
      stopped: { label: '已停止', className: 'bg-gray-500' },
      error: { label: '错误', className: 'bg-red-500' },
      success: { label: '成功', className: 'bg-green-500' },
      failed: { label: '失败', className: 'bg-red-500' },
    };
    const variant = variants[status] || variants.stopped;
    return <Badge className={variant.className}>{variant.label}</Badge>;
  };

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-96">
        <div className="text-muted-foreground">加载中...</div>
      </div>
    );
  }

  if (!adapter) {
    return (
      <div className="p-6">
        <div className="text-center py-12">
          <AlertCircle className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">适配器不存在</p>
          <Button onClick={() => router.push('/collection')} className="mt-4">
            返回列表
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.push('/collection')}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold">{adapter.name}</h1>
              {getStatusBadge(adapter.status)}
            </div>
            <p className="text-muted-foreground mt-1">适配器详情和运行数据</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadAdapterDetails} className="gap-2">
            <RefreshCw className="w-4 h-4" />刷新
          </Button>
          <Button
            variant={adapter.status === 'running' ? 'destructive' : 'default'}
            onClick={handleStartStop}
            className="gap-2"
          >
            {adapter.status === 'running' ? (
              <>
                <Square className="w-4 h-4" />
                停止采集
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                启动采集
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="p-4">
          <div className="text-sm text-muted-foreground">总运行次数</div>
          <div className="text-2xl font-bold mt-1">{adapter.total_runs}</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-muted-foreground">成功次数</div>
          <div className="text-2xl font-bold mt-1 text-green-600">{adapter.successful_runs}</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-muted-foreground">失败次数</div>
          <div className="text-2xl font-bold mt-1 text-red-600">{adapter.failed_runs}</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-muted-foreground">成功率</div>
          <div className="text-2xl font-bold mt-1">
            {adapter.total_runs > 0
              ? `${((adapter.successful_runs / adapter.total_runs) * 100).toFixed(1)}%`
              : 'N/A'}
          </div>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList>
          <TabsTrigger value="info">基本信息</TabsTrigger>
          <TabsTrigger value="history">运行历史</TabsTrigger>
          <TabsTrigger value="data">采集数据</TabsTrigger>
        </TabsList>

        <TabsContent value="info" className="space-y-4">
          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-4">适配器配置</h2>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <div className="text-sm text-muted-foreground">适配器ID</div>
                <div className="font-mono text-sm mt-1">{adapter.id}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">脚本文件</div>
                <div className="font-mono text-sm mt-1">{adapter.script_file}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">数据源</div>
                <div className="mt-1">{source?.name || adapter.source_id}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">数据主题</div>
                <div className="mt-1">{adapter.topic_name}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">创建时间</div>
                <div className="text-sm mt-1">
                  {adapter.created_at ? new Date(adapter.created_at).toLocaleString('zh-CN') : '-'}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">最后运行</div>
                <div className="text-sm mt-1">
                  {adapter.last_run_at
                    ? new Date(adapter.last_run_at).toLocaleString('zh-CN')
                    : '从未运行'}
                </div>
              </div>
            </div>
          </Card>

          {source && (
            <Card className="p-6">
              <h2 className="text-lg font-semibold mb-4">数据源信息</h2>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <div className="text-sm text-muted-foreground">名称</div>
                  <div className="mt-1">{source.name}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">域名</div>
                  <div className="mt-1">{source.domain}</div>
                </div>
                <div className="md:col-span-2">
                  <div className="text-sm text-muted-foreground">描述</div>
                  <div className="mt-1">{source.description}</div>
                </div>
              </div>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card className="p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">运行历史</h2>
                <span className="text-sm text-muted-foreground">最近 {runHistory.length} 条记录</span>
              </div>
              {runHistory.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">暂无运行历史</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="pb-3 font-medium">运行ID</th>
                        <th className="pb-3 font-medium">状态</th>
                        <th className="pb-3 font-medium">采集记录数</th>
                        <th className="pb-3 font-medium">开始时间</th>
                        <th className="pb-3 font-medium">完成时间</th>
                        <th className="pb-3 font-medium">耗时</th>
                        <th className="pb-3 font-medium">错误信息</th>
                      </tr>
                    </thead>
                    <tbody>
                      {runHistory.map((run) => {
                        const duration = run.completed_at
                          ? Math.round(
                              (new Date(run.completed_at).getTime() -
                                new Date(run.started_at).getTime()) /
                                1000
                            )
                          : null;
                        return (
                          <tr key={run.id} className="border-b hover:bg-muted/50">
                            <td className="py-4 font-mono text-xs">{run.id.slice(0, 8)}...</td>
                            <td className="py-4">{getStatusBadge(run.status || 'running')}</td>
                            <td className="py-4">{run.new_records ?? 0}</td>
                            <td className="py-4 text-sm">
                              {new Date(run.started_at).toLocaleString('zh-CN')}
                            </td>
                            <td className="py-4 text-sm">
                              {run.completed_at
                                ? new Date(run.completed_at).toLocaleString('zh-CN')
                                : '运行中'}
                            </td>
                            <td className="py-4 text-sm">
                              {duration !== null ? `${duration}秒` : '-'}
                            </td>
                            <td className="py-4 text-sm text-red-500">
                              {run.error_message || '-'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="data" className="space-y-4">
          <Card className="p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">采集数据</h2>
                <span className="text-sm text-muted-foreground">最近 {collectedData.length} 条记录</span>
              </div>
              {collectedData.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">暂无采集数据</div>
              ) : (
                <div className="space-y-3">
                  {collectedData.map((record) => (
                    <Card key={record.id} className="p-4 bg-muted/30">
                      <div className="flex items-start justify-between mb-2">
                        <span className="text-xs font-mono text-muted-foreground">
                          {record.id.slice(0, 8)}...
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {new Date(record.collected_at).toLocaleString('zh-CN')}
                        </span>
                      </div>
                      <pre className="text-xs bg-background p-3 rounded border overflow-x-auto">
                        {JSON.stringify(record, null, 2)}
                      </pre>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
