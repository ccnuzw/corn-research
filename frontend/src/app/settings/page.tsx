// 系统设置页面
'use client'

import { AppLayout } from '@/components/layout/app-layout'
import { Breadcrumb } from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import { Settings, Bell, Database, Lock, Palette, Zap } from 'lucide-react'

export default function SettingsPage() {
  return (
    <AppLayout title="系统设置">
      <div className="space-y-6">
        {/* 面包屑 */}
        <Breadcrumb
          items={[
            { label: '控制台', href: '/' },
            { label: '系统设置', icon: <Settings className="w-4 h-4" /> },
          ]}
        />

        {/* 设置分组 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 通知设置 */}
          <div className="rounded-lg border border-border/60 bg-card p-6">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <Bell className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <h3 className="font-semibold">通知设置</h3>
                <p className="text-xs text-muted-foreground">配置系统通知和告警</p>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">采集完成通知</div>
                  <div className="text-xs text-muted-foreground">数据采集任务完成时发送通知</div>
                </div>
                <input
                  type="checkbox"
                  defaultChecked
                  className="w-4 h-4 rounded border-border"
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">采集失败告警</div>
                  <div className="text-xs text-muted-foreground">采集任务失败时立即告警</div>
                </div>
                <input
                  type="checkbox"
                  defaultChecked
                  className="w-4 h-4 rounded border-border"
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">质量异常提醒</div>
                  <div className="text-xs text-muted-foreground">数据质量低于阈值时提醒</div>
                </div>
                <input
                  type="checkbox"
                  defaultChecked
                  className="w-4 h-4 rounded border-border"
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">系统状态通知</div>
                  <div className="text-xs text-muted-foreground">系统异常或资源告警</div>
                </div>
                <input
                  type="checkbox"
                  defaultChecked
                  className="w-4 h-4 rounded border-border"
                />
              </div>
            </div>

            <div className="mt-5 pt-5 border-t border-border/60">
              <Button size="sm">保存设置</Button>
            </div>
          </div>

          {/* 数据库设置 */}
          <div className="rounded-lg border border-border/60 bg-card p-6">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                <Database className="w-5 h-5 text-green-500" />
              </div>
              <div>
                <h3 className="font-semibold">数据库设置</h3>
                <p className="text-xs text-muted-foreground">配置数据库连接和优化</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium block mb-2">连接池大小</label>
                <input
                  type="number"
                  defaultValue={20}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  最大并发数据库连接数
                </p>
              </div>

              <div>
                <label className="text-sm font-medium block mb-2">查询超时 (秒)</label>
                <input
                  type="number"
                  defaultValue={30}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  数据库查询的最大等待时间
                </p>
              </div>

              <div>
                <label className="text-sm font-medium block mb-2">数据保留天数</label>
                <input
                  type="number"
                  defaultValue={365}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  原始数据保留时间，超期自动归档
                </p>
              </div>
            </div>

            <div className="mt-5 pt-5 border-t border-border/60">
              <Button size="sm">保存设置</Button>
            </div>
          </div>

          {/* 安全设置 */}
          <div className="rounded-lg border border-border/60 bg-card p-6">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center">
                <Lock className="w-5 h-5 text-red-500" />
              </div>
              <div>
                <h3 className="font-semibold">安全设置</h3>
                <p className="text-xs text-muted-foreground">API密钥和访问控制</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium block mb-2">API 密钥</label>
                <div className="flex gap-2">
                  <input
                    type="password"
                    defaultValue="sk_live_xxxxxxxxxxxx"
                    className="flex-1 px-3 py-2 rounded-lg border border-border bg-background text-sm font-mono"
                    readOnly
                  />
                  <Button size="sm" variant="outline">
                    重新生成
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  用于外部系统访问 API
                </p>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">IP 白名单</div>
                  <div className="text-xs text-muted-foreground">
                    仅允许白名单IP访问系统
                  </div>
                </div>
                <input
                  type="checkbox"
                  className="w-4 h-4 rounded border-border"
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">请求频率限制</div>
                  <div className="text-xs text-muted-foreground">
                    限制单个IP的请求频率
                  </div>
                </div>
                <input
                  type="checkbox"
                  defaultChecked
                  className="w-4 h-4 rounded border-border"
                />
              </div>

              <div>
                <label className="text-sm font-medium block mb-2">会话超时 (分钟)</label>
                <input
                  type="number"
                  defaultValue={60}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm"
                />
              </div>
            </div>

            <div className="mt-5 pt-5 border-t border-border/60">
              <Button size="sm">保存设置</Button>
            </div>
          </div>

          {/* 性能优化 */}
          <div className="rounded-lg border border-border/60 bg-card p-6">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <Zap className="w-5 h-5 text-purple-500" />
              </div>
              <div>
                <h3 className="font-semibold">性能优化</h3>
                <p className="text-xs text-muted-foreground">缓存和性能调优</p>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">启用 Redis 缓存</div>
                  <div className="text-xs text-muted-foreground">
                    缓存常用查询结果
                  </div>
                </div>
                <input
                  type="checkbox"
                  defaultChecked
                  className="w-4 h-4 rounded border-border"
                />
              </div>

              <div>
                <label className="text-sm font-medium block mb-2">缓存过期时间 (秒)</label>
                <input
                  type="number"
                  defaultValue={300}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm"
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">查询结果分页</div>
                  <div className="text-xs text-muted-foreground">
                    自动分页大结果集
                  </div>
                </div>
                <input
                  type="checkbox"
                  defaultChecked
                  className="w-4 h-4 rounded border-border"
                />
              </div>

              <div>
                <label className="text-sm font-medium block mb-2">
                  每页最大记录数
                </label>
                <input
                  type="number"
                  defaultValue={100}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm"
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">启用 Gzip 压缩</div>
                  <div className="text-xs text-muted-foreground">
                    压缩 API 响应数据
                  </div>
                </div>
                <input
                  type="checkbox"
                  defaultChecked
                  className="w-4 h-4 rounded border-border"
                />
              </div>
            </div>

            <div className="mt-5 pt-5 border-t border-border/60">
              <Button size="sm">保存设置</Button>
            </div>
          </div>

          {/* 界面主题 */}
          <div className="rounded-lg border border-border/60 bg-card p-6 lg:col-span-2">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-lg bg-orange-500/10 flex items-center justify-center">
                <Palette className="w-5 h-5 text-orange-500" />
              </div>
              <div>
                <h3 className="font-semibold">界面主题</h3>
                <p className="text-xs text-muted-foreground">自定义系统外观</p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-lg border-2 border-border p-4 cursor-pointer hover:border-primary transition-colors">
                <div className="aspect-video bg-gradient-to-br from-gray-900 to-gray-800 rounded mb-2" />
                <div className="text-sm font-medium text-center">深色主题</div>
                <div className="text-xs text-muted-foreground text-center">当前使用</div>
              </div>

              <div className="rounded-lg border-2 border-transparent p-4 cursor-pointer hover:border-primary transition-colors opacity-50">
                <div className="aspect-video bg-gradient-to-br from-gray-100 to-white rounded mb-2" />
                <div className="text-sm font-medium text-center">浅色主题</div>
                <div className="text-xs text-muted-foreground text-center">即将推出</div>
              </div>

              <div className="rounded-lg border-2 border-transparent p-4 cursor-pointer hover:border-primary transition-colors opacity-50">
                <div className="aspect-video bg-gradient-to-br from-blue-900 to-purple-900 rounded mb-2" />
                <div className="text-sm font-medium text-center">高对比度</div>
                <div className="text-xs text-muted-foreground text-center">即将推出</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
