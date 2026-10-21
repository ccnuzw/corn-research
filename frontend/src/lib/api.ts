// API 客户端
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:18000'

export interface ApiResponse<T> {
  success: boolean
  data?: T
  message?: string
}

export interface Source {
  id: string
  name: string
  domain: string | null
  description: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface Adapter {
  id: string
  name: string
  script_file: string
  source_id: string
  topic_name: string
  status: string
  last_run_at: string | null
  last_cursor: string | null
  total_runs: number
  successful_runs: number
  failed_runs: number
  last_error: string | null
  created_at: string
  updated_at: string
}

export interface AdapterWithSource {
  adapter: Adapter
  source: Source | null
}

export interface CollectionRun {
  id: string
  adapter_id: string
  started_at: string
  completed_at: string | null
  status: string | null
  new_records: number | null
  duplicate_records: number | null
  failed_records: number | null
  start_cursor: string | null
  end_cursor: string | null
  error_message: string | null
}

export interface CollectionRecord {
  id: string
  adapter_id: string
  business_date: string
  value: number | null
  unit: string | null
  topic_name: string | null
  source_url: string | null
  source_html_path: string | null
  quality_grade: string | null
  quality_score: number | null
  collected_at: string
  created_at: string
}

export interface RunResult {
  run_id: string
  status: string
  message: string
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('API request failed:', error)
      throw error
    }
  }

  // 数据源管理
  async listSources() {
    return this.request<Source[]>('/api/sources')
  }

  async getSource(id: string) {
    return this.request<Source>(`/api/sources/${id}`)
  }

  async createSource(data: {
    id: string
    name: string
    domain?: string
    description?: string
  }) {
    return this.request<Source>('/api/sources', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateSource(id: string, data: {
    name?: string
    domain?: string
    description?: string
    status?: string
  }) {
    return this.request<Source>(`/api/sources/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteSource(id: string) {
    return this.request<string>(`/api/sources/${id}`, {
      method: 'DELETE',
    })
  }

  // 适配器管理
  async listAdapters() {
    return this.request<AdapterWithSource[]>('/api/adapters')
  }

  async getAdapter(id: string) {
    return this.request<AdapterWithSource>(`/api/adapters/${id}`)
  }

  async createAdapter(data: {
    id: string
    name: string
    script_file: string
    source_id: string
    topic_name: string
  }) {
    return this.request<Adapter>('/api/adapters', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateAdapter(id: string, data: {
    name?: string
    script_file?: string
    topic_name?: string
  }) {
    return this.request<Adapter>(`/api/adapters/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteAdapter(id: string) {
    return this.request<string>(`/api/adapters/${id}`, {
      method: 'DELETE',
    })
  }

  // 适配器操作
  async runAdapter(id: string) {
    return this.request<RunResult>(`/api/adapters/${id}/run`, {
      method: 'POST',
    })
  }

  async startAdapter(id: string) {
    return this.request<Adapter>(`/api/adapters/${id}/start`, {
      method: 'POST',
    })
  }

  async stopAdapter(id: string) {
    return this.request<Adapter>(`/api/adapters/${id}/stop`, {
      method: 'POST',
    })
  }

  async getAdapterRuns(id: string, limit?: number) {
    const query = limit ? `?limit=${limit}` : ''
    return this.request<CollectionRun[]>(`/api/adapters/${id}/runs${query}`)
  }

  async getAdapterRecords(id: string, limit?: number) {
    const query = limit ? `?limit=${limit}` : ''
    return this.request<CollectionRecord[]>(`/api/adapters/${id}/records${query}`)
  }
}

// 导出单例
export const api = new ApiClient()
