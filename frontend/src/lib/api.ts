// API Client - 连接真实后端
// 后端运行在 http://localhost:18000

const API_BASE = typeof window !== 'undefined' 
  ? (window.location.hostname === 'localhost' ? 'http://localhost:18000' : '/api')
  : 'http://localhost:18000'

export interface CollectorInfo {
  id: string
  name: string
  status: 'running' | 'idle' | 'error' | 'ready'
  last_run?: string
  nextRun?: string
  success_rate?: number
  total_runs?: number
  last_success?: string
}

export interface DataPoint {
  date: string
  value: number
  indicator: string
  region: string
}

export interface SystemStats {
  totalRecords: number
  todayCollected: number
  activeCollectors: number
  dataQuality: number
}

export interface ScheduledJob {
  id: string
  name: string
  collector_id: string
  cron_expr: string
  enabled: boolean
  last_run?: string
  next_run?: string
  status: string
}

export interface QualityScore {
  indicator: string
  score: number
  grade: string
  issues: string[]
}

export interface QualityDistribution {
  grade_a: number
  grade_b: number
  grade_c: number
  grade_d: number
}

// API响应包装
interface ApiResponse<T> {
  success: boolean
  data?: T
  message?: string
}

// 通用请求函数
async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })
    
    if (!response.ok) {
      // 尝试解析错误响应体
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`
      try {
        const errorData = await response.json()
        if (errorData.message) {
          errorMessage = errorData.message
        }
      } catch {
        // 如果响应体不是 JSON，使用默认错误消息
      }
      console.error(`API Error [${endpoint}]:`, errorMessage)
      throw new Error(errorMessage)
    }
    
    const result: ApiResponse<T> = await response.json()
    
    if (!result.success) {
      const errorMessage = result.message || 'API request failed'
      console.error(`API Error [${endpoint}]:`, errorMessage)
      throw new Error(errorMessage)
    }
    
    return result.data as T
  } catch (error) {
    console.error(`API Error [${endpoint}]:`, error)
    // 重新抛出错误，让调用方处理
    throw error
  }
}

export const api = {
  // 采集器API
  async getCollectors(): Promise<CollectorInfo[]> {
    return request<CollectorInfo[]>('/api/collectors')
  },
  
  async runCollector(id: string): Promise<{ collector_id: string; records_collected: number }> {
    return request(`/api/collectors/${id}/run`, { method: 'POST' })
  },
  
  async getCollectorHistory(id: string, limit = 50) {
    return request(`/api/collectors/${id}/history?limit=${limit}`)
  },
  
  async getCollectorStatus(id: string): Promise<CollectorInfo> {
    return request<CollectorInfo>(`/api/collectors/${id}/status`)
  },
  
  // 数据API
  async getLatestData(indicator?: string, days = 30, limit = 100): Promise<DataPoint[]> {
    const params = new URLSearchParams()
    if (indicator) params.append('indicator', indicator)
    params.append('days', days.toString())
    params.append('limit', limit.toString())
    
    return request<DataPoint[]>(`/api/data/latest?${params}`)
  },
  
  async getTrendData(indicator: string, days = 30): Promise<DataPoint[]> {
    return request<DataPoint[]>(`/api/data/trend?indicator=${indicator}&days=${days}`)
  },
  
  async getStats(): Promise<SystemStats> {
    return request<SystemStats>('/api/data/stats')
  },
  
  async getIndicators() {
    return request('/api/data/indicators')
  },
  
  // 定时任务API
  async getJobs(): Promise<ScheduledJob[]> {
    return request<ScheduledJob[]>('/api/scheduler/jobs')
  },
  
  async createJob(data: {
    name: string
    collector_id: string
    cron_expression: string
    description?: string
    enabled?: boolean
  }) {
    return request('/api/scheduler/jobs', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
  
  async updateJob(id: string, data: {
    name?: string
    cron_expression?: string
    description?: string
  }) {
    return request(`/api/scheduler/jobs/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },
  
  async deleteJob(id: string) {
    return request(`/api/scheduler/jobs/${id}`, { method: 'DELETE' })
  },
  
  async toggleJob(id: string, enabled: boolean) {
    return request(`/api/scheduler/jobs/${id}/enable`, {
      method: 'PUT',
      body: JSON.stringify({ enabled }),
    })
  },
  
  async triggerJob(id: string) {
    return request(`/api/scheduler/jobs/${id}`, { method: 'POST' })
  },
  
  // 数据质量API
  async getQualityScores(): Promise<QualityScore[]> {
    return request<QualityScore[]>('/api/quality/scores')
  },
  
  async getQualityDistribution(): Promise<QualityDistribution> {
    return request<QualityDistribution>('/api/quality/distribution')
  },
  
  async getQualityIssues() {
    return request('/api/quality/issues')
  },
  
  // 通知API
  async getNotifications(limit = 50) {
    return request(`/api/notifications?limit=${limit}`)
  },
  
  async markNotificationRead(notification_id: string) {
    return request('/api/notifications/mark-read', {
      method: 'POST',
      body: JSON.stringify({ notification_id }),
    })
  },
  
  // 健康检查
  async healthCheck(): Promise<{ status: string; message?: string }> {
    try {
      const response = await fetch(`${API_BASE}/health`)
      const data = await response.json()
      return { status: data.success ? 'ok' : 'error', message: data.data }
    } catch (error) {
      return { status: 'error', message: String(error) }
    }
  },
}
