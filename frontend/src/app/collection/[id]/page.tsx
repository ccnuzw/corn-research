'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { AppLayout } from '@/components/layout/app-layout';
import { Breadcrumb } from '@/components/ui/breadcrumb';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArrowLeft, Play, Square, RefreshCw, AlertCircle, Database, Clock, CheckCircle, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import { api, type AdapterWithSource, type CollectionRun, type CollectionRecord } from '@/lib/api';

export default function AdapterDetailPage() {
  const router = useRouter();
  const params = useParams();
  const adapterId = params.id as string;

  const [adapter, setAdapter] = useState<AdapterWithSource | null>(null);
  const [runHistory, setRunHistory] = useState<CollectionRun[]>([]);
  const [collectedData, setCollectedData] = useState<CollectionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningCollection, setRunningCollection] = useState(false);
  const [activeTab, setActiveTab] = useState('history');

  const loadAdapterDetails = useCallback(async () => {
    setLoading(true);
    try {
      const [adapterData, historyData, recordsData] = await Promise.all([
        api.getAdapter(adapterId),
        api.getAdapterRuns(adapterId, 20),
        api.getAdapterRecords(adapterId, 50),
      ]);

      if (adapterData.success && adapterData.data) {
        setAdapter(adapterData.data);
        setRunHistory(historyData.data || []);
        setCollectedData(recordsData.data || []);
      } else {
        toast.error('适配器不存在');
        router.push('/collectors');
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
    // 每10秒自动刷新
    const interval = setInterval(loadAdapterDetails, 10000);
    return () => clearInterval(interval);
  }, [loadAdapterDetails]);

  const handleRunNow = async () => {
    if (!adapter || runningCollection) return;

    setRunningCollection(true);
    try {
      toast.loading(`开始采集: ${adapter.name}`, { id: 'run-now' });
      
      const response = await api.runAdapter(adapterId);
      
      if (response.success && response.data) {
        toast.success(
          `采集成功: ${adapter.name}`,
          {
            id: 'run-now',
            description: response.data.message || '采集任务已完成',
            duration: 5000,
          }
        );
        // 刷新数据
        await loadAdapterDetails();
      } else {
        toast.error(
          `采集失败: ${adapter.name}`,
          {
            id: 'run-now',
            description: response.message || '未知错误',
            duration: 5000,
          }
        );
      }
    } catch (error) {
      console.error('Failed to run adapter:', error);
      toast.error(
        `采集失败: ${adapter.name}`,
        {
          id: 'run-now',
          description: error instanceof Error ? error.message : '网络错误',
          duration: 5000,
        }
      );
    } finally {
      setRunningCollection(false);
    }
  };

  const handleStartStop = async () => {
    if (!adapter) return;

    const action = adapter.status === 'running' ? 'stop' : 'start';
    try {
      const result = action === 'stop'
        ? await api.stopAdapter(adapterId)
        : await api.startAdapter(adapterId);

      if (result.success) {
        toast.success(action === 'start' ? '定时任务已启动' : '定时任务已停止');
        await loadAdapterDetails();
      } else {
        toast.error(result.message || `${action === 'start' ? '启动' : '停止'}失败`);
      }
    } catch (error) {
      console.error(`Failed to ${action} adapter:`, error);
      toast.error(`${action === 'start' ? '启动' : '停止'}定时任务失败`);
    }
  };

  const getStatusBadge = (status: string | null) => {
    const statusMap: Record<string, { label: string; variant: 'success' | 'destructive' | 'secondary' | 'default' }> = {
      running: { label: '运行中', variant: 'secondary' },
      stopped: { label: '已停止', variant: 'secondary' },
      error: { label: '错误', variant: 'destructive' },
      success: { label: '成功', variant: 'success' },
      failed: { label: '失败', variant: 'destructive' },
    };
    const statusInfo = statusMap[status || 'stopped'] || statusMap.stopped;
    return (
      <Badge variant={statusInfo.variant} className="rounded-full">
        {statusInfo.label}
      </Badge>
    );
  };

  const formatDuration = (startedAt: string, completedAt: string | null) => {
    if (!completedAt) return '-';
    const start = new Date(startedAt).getTime();
    const end = new Date(completedAt).getTime();
    const durationMs = end - start;
    
    if (durationMs < 1000) return `${durationMs}ms`;
    if (durationMs < 60000) return `${(durationMs / 1000).toFixed(2)}s`;
    return `${(durationMs / 60000).toFixed(1)}min`;
  };

  const formatDateTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const formatRelativeTime = (dateStr: string | null) => {
    if (!dateStr) return '从未运行';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    return `${days}天前`;
  };

  if (loading) {
    return (
      <AppLayout title="采集器详情">
        <div className="flex items-center justify-center h-96">
          <RefreshCw className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      </AppLayout>
    );
  }

  if (!adapter) {
    return (
      <AppLayout title="采集器详情">
        <div className="text-center py-12">
          <AlertCircle className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">适配器不存在</p>
          <Button onClick={() => router.push('/collectors')} className="mt-4">
            返回列表
          </Button>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title={adapter.name} subtitle="采集器详情和运行历史">
      <div className="space-y-4">
        {/* 面包屑 */}
        <Breadcrumb
          items={[
            { label: '控制台', href: '/' },
            { label: '采集器管理', href: '/collectors' },
            { label: adapter.name, icon: <Database className="w-4 h-4" /> },
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
                <div className="text-2xl font-bold">{adapter.total_runs}</div>
                <div className="text-xs text-muted-foreground">总运行次数</div>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-border/60 bg-card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-green-500" />
              </div>
              <div>
                <div className="text-2xl font-bold text-green-600">{adapter.successful_runs}</div>
                <div className="text-xs text-muted-foreground">成功次数</div>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-border/60 bg-card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center">
                <XCircle className="w-5 h-5 text-red-500" />
              </div>
              <div>
                <div className="text-2xl font-bold text-red-600">{adapter.failed_runs}</div>
                <div className="text-xs text-muted-foreground">失败次数</div>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-border/60 bg-card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <Clock className="w-5 h-5 text-purple-500" />
              </div>
              <div>
                <div className="text-2xl font-bold">
                  {adapter.total_runs > 0
                    ? `${((adapter.successful_runs / adapter.total_runs) * 100).toFixed(1)}%`
                    : 'N/A'}
                </div>
                <div className="text-xs text-muted-foreground">成功率</div>
              </div>
            </div>
          </div>
        </div>

        {/* 操作按钮栏 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              onClick={handleRunNow}
              disabled={runningCollection}
              className="gap-1.5"
            >
              {runningCollection ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  采集中
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5" />
                  立即采集
                </>
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleStartStop}
              className="gap-1.5"
            >
              {adapter.status === 'running' ? (
                <>
                  <Square className="w-3.5 h-3.5" />
                  停止定时任务
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5" />
                  启动定时任务
                </>
              )}
            </Button>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              最后运行: {formatRelativeTime(adapter.last_run_at)}
            </span>
            <Button variant="outline" size="sm" onClick={loadAdapterDetails} disabled={loading}>
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList>
            <TabsTrigger value="history">运行历史</TabsTrigger>
            <TabsTrigger value="data">采集数据</TabsTrigger>
            <TabsTrigger value="info">基本信息</TabsTrigger>
          </TabsList>

          <TabsContent value="history">
            <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
              <div className="p-5 border-b border-border/60">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-base font-semibold">运行历史</h3>
                    <p className="text-sm text-muted-foreground mt-1">最近 {runHistory.length} 条运行记录</p>
                  </div>
                  {getStatusBadge(adapter.status)}
                </div>
              </div>

              {runHistory.length === 0 ? (
                <div className="p-12 text-center text-muted-foreground">
                  <Clock className="w-12 h-12 mx-auto mb-4 opacity-20" />
                  <p>暂无运行历史</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-muted/50">
                      <tr className="h-11">
                        <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                          开始时间
                        </th>
                        <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                          持续时间
                        </th>
                        <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                          状态
                        </th>
                        <th className="px-4 text-right text-[12px] font-medium text-muted-foreground">
                          新记录
                        </th>
                        <th className="px-4 text-right text-[12px] font-medium text-muted-foreground">
                          重复
                        </th>
                        <th className="px-4 text-right text-[12px] font-medium text-muted-foreground">
                          失败
                        </th>
                        <th className="px-4 text-left text-[12px] font-medium text-muted-foreground">
                          错误信息
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {runHistory.map((run) => (
                        <tr
                          key={run.id}
                          className="h-14 border-b border-border hover:bg-accent/50 transition-colors"
                        >
                          <td className="px-4 text-[13px]">
                            {formatDateTime(run.started_at)}
                          </td>
                          <td className="px-4 text-[13px] font-mono">
                            {formatDuration(run.started_at, run.completed_at)}
                          </td>
                          <td className="px-4">
                            {getStatusBadge(run.status)}
                          </td>
                          <td className="px-4 text-right text-[13px] font-mono font-semibold text-green-600">
                            {run.new_records ?? 0}
                          </td>
                          <td className="px-4 text-right text-[13px] font-mono text-muted-foreground">
                            {run.duplicate_records ?? 0}
                          </td>
                          <td className="px-4 text-right text-[13px] font-mono text-red-600">
                            {run.failed_records ?? 0}
                          </td>
                          <td className="px-4 text-[13px] text-red-500">
                            {run.error_message ? (
                              <span className="truncate block max-w-xs" title={run.error_message}>
                                {run.error_message}
                              </span>
                            ) : (
                              '-'
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="data">
            <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
              <div className="p-5 border-b border-border/60">
                <h3 className="text-base font-semibold">采集数据</h3>
                <p className="text-sm text-muted-foreground mt-1">最近 {collectedData.length} 条数据记录</p>
              </div>

              {collectedData.length === 0 ? (
                <div className="p-12 text-center text-muted-foreground">
                  <Database className="w-12 h-12 mx-auto mb-4 opacity-20" />
                  <p>暂无采集数据</p>
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
                          采集时间
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {collectedData.map((record) => (
                        <tr
                          key={record.id}
                          className="h-12 border-b border-border hover:bg-accent/50 transition-colors"
                        >
                          <td className="px-4 text-[13px] font-mono">
                            {record.business_date}
                          </td>
                          <td className="px-4 text-[13px]">
                            {record.topic_name || '-'}
                          </td>
                          <td className="px-4 text-right text-[13px] font-mono font-semibold">
                            {record.value?.toFixed(2) || '-'}
                          </td>
                          <td className="px-4 text-[13px] text-muted-foreground">
                            {record.unit || '-'}
                          </td>
                          <td className="px-4 text-[13px] text-muted-foreground">
                            {formatDateTime(record.collected_at)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="info">
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
                  <div className="mt-1">{adapter.source?.name || adapter.source_id}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">数据主题</div>
                  <div className="mt-1">{adapter.topic_name}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">创建时间</div>
                  <div className="text-sm mt-1">
                    {adapter.created_at ? formatDateTime(adapter.created_at) : '-'}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">最后运行</div>
                  <div className="text-sm mt-1">
                    {adapter.last_run_at ? formatDateTime(adapter.last_run_at) : '从未运行'}
                  </div>
                </div>
              </div>

              {adapter.source && (
                <>
                  <div className="border-t my-6" />
                  <h2 className="text-lg font-semibold mb-4">数据源信息</h2>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <div className="text-sm text-muted-foreground">名称</div>
                      <div className="mt-1">{adapter.source.name}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">域名</div>
                      <div className="mt-1">{adapter.source.domain || '-'}</div>
                    </div>
                    {adapter.source.description && (
                      <div className="md:col-span-2">
                        <div className="text-sm text-muted-foreground">描述</div>
                        <div className="mt-1">{adapter.source.description}</div>
                      </div>
                    )}
                  </div>
                </>
              )}
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  );
}
