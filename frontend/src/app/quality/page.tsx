// 数据质量页面
'use client'

import { AppLayout } from '@/components/layout/app-layout'
import { Breadcrumb } from '@/components/ui/breadcrumb'
import { Badge } from '@/components/ui/badge'
import { Shield, AlertTriangle, CheckCircle2, XCircle, Info } from 'lucide-react'

export default function QualityPage() {
  // Mock 数据
  const qualityStats = {
    total: 1248,
    gradeA: 856,
    gradeB: 287,
    gradeC: 82,
    gradeD: 23,
  }

  const qualityIssues = [
    {
      id: '1',
      type: 'missing_field',
      severity: 'high',
      count: 15,
      description: '缺少必填字段：region',
      affectedRecords: ['record_001', 'record_002', 'record_003'],
    },
    {
      id: '2',
      type: 'invalid_value',
      severity: 'medium',
      count: 8,
      description: '数值超出合理范围（价格 > 5000）',
      affectedRecords: ['record_010', 'record_011'],
    },
    {
      id: '3',
      type: 'duplicate',
      severity: 'low',
      count: 3,
      description: '重复记录（相同日期+相同指标）',
      affectedRecords: ['record_020'],
    },
  ]

  const getPercentage = (count: number) => {
    return ((count / qualityStats.total) * 100).toFixed(1)
  }

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'high':
        return <Badge variant="destructive">高</Badge>
      case 'medium':
        return <Badge variant="default">中</Badge>
      case 'low':
        return <Badge variant="secondary">低</Badge>
      default:
        return <Badge variant="outline">未知</Badge>
    }
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'high':
        return <XCircle className="w-5 h-5 text-destructive" />
      case 'medium':
        return <AlertTriangle className="w-5 h-5 text-orange-500" />
      case 'low':
        return <Info className="w-5 h-5 text-blue-500" />
      default:
        return <Info className="w-5 h-5 text-muted-foreground" />
    }
  }

  return (
    <AppLayout title="数据质量">
      <div className="space-y-6">
        {/* 面包屑 */}
        <Breadcrumb
          items={[
            { label: '控制台', href: '/' },
            { label: '数据质量', icon: <Shield className="w-4 h-4" /> },
          ]}
        />

        {/* 质量概览 */}
        <div className="rounded-lg border border-border/60 bg-card p-6">
          <h2 className="text-lg font-semibold mb-4">质量评分分布</h2>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {/* 总计 */}
            <div className="rounded-lg border border-border/60 p-4">
              <div className="text-3xl font-bold mb-1">{qualityStats.total}</div>
              <div className="text-sm text-muted-foreground">总记录数</div>
            </div>

            {/* A级 */}
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                <Badge variant="success">A</Badge>
              </div>
              <div className="text-2xl font-bold mb-1">{qualityStats.gradeA}</div>
              <div className="text-sm text-muted-foreground">
                {getPercentage(qualityStats.gradeA)}% 优秀
              </div>
            </div>

            {/* B级 */}
            <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 className="w-5 h-5 text-blue-500" />
                <Badge variant="default">B</Badge>
              </div>
              <div className="text-2xl font-bold mb-1">{qualityStats.gradeB}</div>
              <div className="text-sm text-muted-foreground">
                {getPercentage(qualityStats.gradeB)}% 良好
              </div>
            </div>

            {/* C级 */}
            <div className="rounded-lg border border-orange-500/20 bg-orange-500/5 p-4">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-5 h-5 text-orange-500" />
                <Badge variant="outline">C</Badge>
              </div>
              <div className="text-2xl font-bold mb-1">{qualityStats.gradeC}</div>
              <div className="text-sm text-muted-foreground">
                {getPercentage(qualityStats.gradeC)}% 一般
              </div>
            </div>

            {/* D级 */}
            <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4">
              <div className="flex items-center gap-2 mb-2">
                <XCircle className="w-5 h-5 text-red-500" />
                <Badge variant="destructive">D</Badge>
              </div>
              <div className="text-2xl font-bold mb-1">{qualityStats.gradeD}</div>
              <div className="text-sm text-muted-foreground">
                {getPercentage(qualityStats.gradeD)}% 较差
              </div>
            </div>
          </div>
        </div>

        {/* 质量问题列表 */}
        <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
          <div className="p-5 border-b border-border/60">
            <h3 className="text-base font-semibold">质量问题</h3>
            <p className="text-sm text-muted-foreground mt-1">
              发现 {qualityIssues.length} 类问题，共影响{' '}
              {qualityIssues.reduce((sum, issue) => sum + issue.count, 0)} 条记录
            </p>
          </div>

          <div className="divide-y divide-border/60">
            {qualityIssues.map((issue) => (
              <div key={issue.id} className="p-5 hover:bg-accent/50 transition-colors">
                <div className="flex items-start gap-4">
                  <div className="shrink-0 mt-1">{getSeverityIcon(issue.severity)}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      {getSeverityBadge(issue.severity)}
                      <span className="text-sm font-medium">{issue.description}</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span>影响记录: {issue.count} 条</span>
                      <span>类型: {issue.type}</span>
                    </div>
                    <div className="mt-2">
                      <details className="text-xs">
                        <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                          查看受影响的记录
                        </summary>
                        <div className="mt-2 pl-4 space-y-1">
                          {issue.affectedRecords.map((recordId) => (
                            <div key={recordId} className="font-mono text-muted-foreground">
                              {recordId}
                            </div>
                          ))}
                        </div>
                      </details>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 质量规则说明 */}
        <div className="rounded-lg border border-border/60 bg-card p-6">
          <h3 className="text-base font-semibold mb-4">质量评分规则</h3>
          <div className="space-y-3 text-sm">
            <div className="flex items-start gap-3">
              <Badge variant="success" className="shrink-0">A</Badge>
              <div>
                <div className="font-medium mb-1">优秀（≥90分）</div>
                <div className="text-muted-foreground text-xs">
                  所有必填字段完整，数值在合理范围内，来源可信度高，时效性强
                </div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Badge variant="default" className="shrink-0">B</Badge>
              <div>
                <div className="font-medium mb-1">良好（75-89分）</div>
                <div className="text-muted-foreground text-xs">
                  必填字段完整，数值基本合理，来源可信度中等
                </div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Badge variant="outline" className="shrink-0">C</Badge>
              <div>
                <div className="font-medium mb-1">一般（60-74分）</div>
                <div className="text-muted-foreground text-xs">
                  部分字段缺失，数值可能存在异常，需要人工审核
                </div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Badge variant="destructive" className="shrink-0">D</Badge>
              <div>
                <div className="font-medium mb-1">较差（&lt;60分）</div>
                <div className="text-muted-foreground text-xs">
                  关键字段缺失，数值明显异常，来源不可靠，建议丢弃
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
