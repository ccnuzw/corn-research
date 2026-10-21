// 数据质量监控页面
'use client'

import { useState, useEffect } from 'react'
import { AppLayout } from '@/components/layout/app-layout'
import { Breadcrumb } from '@/components/ui/breadcrumb'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Shield, AlertTriangle, CheckCircle, XCircle, RefreshCw } from 'lucide-react'
import { api, type QualityDistribution } from '@/lib/api'

export default function QualityPage() {
  const [distribution, setDistribution] = useState<QualityDistribution | null>(null)
  const [loading, setLoading] = useState(true)

  const loadQualityData = async () => {
    try {
      setLoading(true)
      const data = await api.getQualityDistribution()
      setDistribution(data)
    } catch (error) {
      console.error('Failed to load quality data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadQualityData()
    const interval = setInterval(loadQualityData, 60000)
    return () => clearInterval(interval)
  }, [])

  const totalRecords = distribution
    ? distribution.grade_a + distribution.grade_b + distribution.grade_c + distribution.grade_d
    : 0

  const getPercentage = (count: number) => {
    if (totalRecords === 0) return 0
    return ((count / totalRecords) * 100).toFixed(1)
  }

  return (
    <AppLayout title="数据质量">
      <div className="space-y-4">
        <Breadcrumb
          items={[
            { label: '控制台', href: '/' },
            { label: '数据质量', icon: <Shield className="w-4 h-4" /> },
          ]}
        />

        {/* 质量概览 */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center">
                <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
                优秀 (A)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold font-mono text-green-400">
                {distribution?.grade_a || 0}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                占比 {getPercentage(distribution?.grade_a || 0)}%
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center">
                <CheckCircle className="w-4 h-4 mr-2 text-blue-500" />
                良好 (B)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold font-mono text-blue-400">
                {distribution?.grade_b || 0}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                占比 {getPercentage(distribution?.grade_b || 0)}%
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center">
                <AlertTriangle className="w-4 h-4 mr-2 text-yellow-500" />
                一般 (C)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold font-mono text-yellow-400">
                {distribution?.grade_c || 0}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                占比 {getPercentage(distribution?.grade_c || 0)}%
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center">
                <XCircle className="w-4 h-4 mr-2 text-red-500" />
                较差 (D)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold font-mono text-red-600">
                {distribution?.grade_d || 0}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                占比 {getPercentage(distribution?.grade_d || 0)}%
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 质量分布可视化 */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>质量等级分布</CardTitle>
              <Button size="sm" variant="outline" onClick={loadQualityData}>
                <RefreshCw className="w-4 h-4 mr-1" />
                刷新
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                加载中...
              </div>
            ) : totalRecords === 0 ? (
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                暂无数据
              </div>
            ) : (
              <div className="space-y-4">
                {/* 进度条可视化 */}
                <div className="space-y-3">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">优秀 (A)</span>
                      <span className="text-sm text-muted-foreground">
                        {distribution?.grade_a || 0} 条 ({getPercentage(distribution?.grade_a || 0)}%)
                      </span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-4">
                      <div
                        className="bg-green-400/100 h-4 rounded-full transition-all"
                        style={{ width: `${getPercentage(distribution?.grade_a || 0)}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">良好 (B)</span>
                      <span className="text-sm text-muted-foreground">
                        {distribution?.grade_b || 0} 条 ({getPercentage(distribution?.grade_b || 0)}%)
                      </span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-4">
                      <div
                        className="bg-blue-400/100 h-4 rounded-full transition-all"
                        style={{ width: `${getPercentage(distribution?.grade_b || 0)}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">一般 (C)</span>
                      <span className="text-sm text-muted-foreground">
                        {distribution?.grade_c || 0} 条 ({getPercentage(distribution?.grade_c || 0)}%)
                      </span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-4">
                      <div
                        className="bg-yellow-400/100 h-4 rounded-full transition-all"
                        style={{ width: `${getPercentage(distribution?.grade_c || 0)}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">较差 (D)</span>
                      <span className="text-sm text-muted-foreground">
                        {distribution?.grade_d || 0} 条 ({getPercentage(distribution?.grade_d || 0)}%)
                      </span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-4">
                      <div
                        className="bg-destructive h-4 rounded-full transition-all"
                        style={{ width: `${getPercentage(distribution?.grade_d || 0)}%` }}
                      />
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t">
                  <div className="text-sm text-muted-foreground">
                    总计: <span className="font-mono font-semibold">{totalRecords}</span> 条数据记录
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 质量改进建议 */}
        <Card>
          <CardHeader>
            <CardTitle>质量改进建议</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-start gap-3 p-3 bg-blue-400/10 rounded-lg">
                <Shield className="w-5 h-5 text-blue-400 mt-0.5" />
                <div className="flex-1">
                  <div className="font-medium text-sm">数据验证规则</div>
                  <div className="text-sm text-muted-foreground mt-1">
                    建议为所有采集器配置数据验证规则，确保采集数据符合预期格式。
                  </div>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-green-400/10 rounded-lg">
                <CheckCircle className="w-5 h-5 text-green-400 mt-0.5" />
                <div className="flex-1">
                  <div className="font-medium text-sm">异常值检测</div>
                  <div className="text-sm text-muted-foreground mt-1">
                    启用自动异常值检测，及时发现并标记可疑数据点。
                  </div>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-yellow-400/10 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-yellow-400 mt-0.5" />
                <div className="flex-1">
                  <div className="font-medium text-sm">数据完整性检查</div>
                  <div className="text-sm text-muted-foreground mt-1">
                    定期检查关键指标的数据完整性，避免缺失数据影响分析结果。
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  )
}
