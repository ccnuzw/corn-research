// 系统监控页面
'use client'

import { useState, useEffect } from 'react'
import { AppLayout } from '@/components/layout/app-layout'
import { Breadcrumb } from '@/components/ui/breadcrumb'
import { Activity, Server, Database, Cpu, HardDrive, Network } from 'lucide-react'

export default function MonitorPage() {
  const [systemStats] = useState({
    cpu: 45.3,
    memory: 62.1,
    disk: 38.7,
    network: 12.5,
  })

  const [services] = useState([
    { name: 'Rust Backend', status: 'healthy', uptime: '6h 24m', port: 18000 },
    { name: 'PostgreSQL', status: 'healthy', uptime: '2d 14h', port: 15432 },
    { name: 'Redis', status: 'healthy', uptime: '2d 14h', port: 16380 },
    { name: 'Next.js Frontend', status: 'healthy', uptime: '1h 15m', port: 3080 },
  ])

  const [recentLogs] = useState([
    { time: '15:28:45', level: 'INFO', message: '✅ Collection completed: 156 records' },
    { time: '15:28:32', level: 'INFO', message: '🐍 Calling Python collector: mock' },
    { time: '15:27:12', level: 'INFO', message: '📊 Run complete: 12 new, 3 duplicate, 0 failed' },
    { time: '15:26:58', level: 'INFO', message: '🚀 Starting collection for adapter: adapter_mock_test' },
    { time: '15:25:30', level: 'WARN', message: '⚠️ Rate limit approaching for sina_production' },
    { time: '15:24:15', level: 'INFO', message: '✅ Database connected' },
  ])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-500'
      case 'warning':
        return 'bg-yellow-500'
      case 'error':
        return 'bg-red-500'
      default:
        return 'bg-gray-500'
    }
  }

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'INFO':
        return 'text-blue-500'
      case 'WARN':
        return 'text-yellow-500'
      case 'ERROR':
        return 'text-red-500'
      default:
        return 'text-gray-500'
    }
  }

  const getProgressColor = (value: number) => {
    if (value < 50) return 'bg-green-500'
    if (value < 80) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  return (
    <AppLayout title="系统监控">
      <div className="space-y-6">
        {/* 面包屑 */}
        <Breadcrumb
          items={[
            { label: '控制台', href: '/' },
            { label: '系统监控', icon: <Activity className="w-4 h-4" /> },
          ]}
        />

        {/* 系统资源 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-lg border border-border/60 bg-card p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Cpu className="w-5 h-5 text-blue-500" />
                <span className="font-medium text-sm">CPU 使用率</span>
              </div>
              <span className="text-2xl font-bold">{systemStats.cpu}%</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={`h-full ${getProgressColor(systemStats.cpu)} transition-all`}
                style={{ width: `${systemStats.cpu}%` }}
              />
            </div>
          </div>

          <div className="rounded-lg border border-border/60 bg-card p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Server className="w-5 h-5 text-green-500" />
                <span className="font-medium text-sm">内存使用</span>
              </div>
              <span className="text-2xl font-bold">{systemStats.memory}%</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={`h-full ${getProgressColor(systemStats.memory)} transition-all`}
                style={{ width: `${systemStats.memory}%` }}
              />
            </div>
          </div>

          <div className="rounded-lg border border-border/60 bg-card p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <HardDrive className="w-5 h-5 text-purple-500" />
                <span className="font-medium text-sm">磁盘使用</span>
              </div>
              <span className="text-2xl font-bold">{systemStats.disk}%</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={`h-full ${getProgressColor(systemStats.disk)} transition-all`}
                style={{ width: `${systemStats.disk}%` }}
              />
            </div>
          </div>

          <div className="rounded-lg border border-border/60 bg-card p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Network className="w-5 h-5 text-orange-500" />
                <span className="font-medium text-sm">网络流量</span>
              </div>
              <span className="text-2xl font-bold">{systemStats.network} MB/s</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-orange-500 transition-all"
                style={{ width: `${Math.min(systemStats.network * 4, 100)}%` }}
              />
            </div>
          </div>
        </div>

        {/* 服务状态 */}
        <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
          <div className="p-5 border-b border-border/60">
            <h3 className="text-base font-semibold">服务状态</h3>
            <p className="text-sm text-muted-foreground mt-1">所有服务运行正常</p>
          </div>

          <div className="divide-y divide-border/60">
            {services.map((service) => (
              <div key={service.name} className="p-5 hover:bg-accent/50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-2 h-2 rounded-full ${getStatusColor(service.status)}`} />
                    <div>
                      <div className="font-medium">{service.name}</div>
                      <div className="text-xs text-muted-foreground">
                        运行时间: {service.uptime} · 端口: {service.port}
                      </div>
                    </div>
                  </div>
                  <div className="text-sm">
                    <span className="text-green-500 font-medium">正常运行</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 实时日志 */}
        <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
          <div className="p-5 border-b border-border/60">
            <h3 className="text-base font-semibold">实时日志</h3>
            <p className="text-sm text-muted-foreground mt-1">最近的系统日志</p>
          </div>

          <div className="divide-y divide-border/60 max-h-96 overflow-y-auto">
            {recentLogs.map((log, index) => (
              <div key={index} className="p-3 hover:bg-accent/50 transition-colors font-mono text-xs">
                <div className="flex items-start gap-3">
                  <span className="text-muted-foreground shrink-0">{log.time}</span>
                  <span className={`font-medium shrink-0 ${getLevelColor(log.level)}`}>
                    {log.level}
                  </span>
                  <span className="flex-1 text-foreground">{log.message}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 数据库连接池 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-lg border border-border/60 bg-card p-5">
            <div className="flex items-center gap-2 mb-4">
              <Database className="w-5 h-5 text-blue-500" />
              <h3 className="font-semibold">数据库连接池</h3>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">活跃连接</span>
                <span className="font-medium">8 / 20</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">空闲连接</span>
                <span className="font-medium">12</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">等待队列</span>
                <span className="font-medium">0</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">平均响应时间</span>
                <span className="font-medium">12ms</span>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-border/60 bg-card p-5">
            <div className="flex items-center gap-2 mb-4">
              <Server className="w-5 h-5 text-red-500" />
              <h3 className="font-semibold">Redis 状态</h3>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">已用内存</span>
                <span className="font-medium">128 MB</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">连接数</span>
                <span className="font-medium">5</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">命中率</span>
                <span className="font-medium">98.5%</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">键总数</span>
                <span className="font-medium">1,247</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
