// 系统设置页面
'use client'

import { AppLayout } from '@/components/layout/app-layout'
import { Breadcrumb } from '@/components/ui/breadcrumb'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Settings } from 'lucide-react'

export default function SettingsPage() {
  return (
    <AppLayout title="系统设置">
      <div className="space-y-4">
        <Breadcrumb
          items={[
            { label: '控制台', href: '/' },
            { label: '系统设置', icon: <Settings className="w-4 h-4" /> },
          ]}
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader>
              <CardTitle>数据源配置</CardTitle>
              <CardDescription>管理数据采集源的连接和认证信息</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" size="sm">配置数据源</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>主题设置</CardTitle>
              <CardDescription>自定义界面主题和配色方案</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" size="sm">切换主题</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>系统日志</CardTitle>
              <CardDescription>查看系统运行日志和错误记录</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" size="sm">查看日志</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>备份恢复</CardTitle>
              <CardDescription>数据备份和系统恢复管理</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" size="sm">备份管理</Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </AppLayout>
  )
}
