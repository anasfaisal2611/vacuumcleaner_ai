import type {
  ApiError,
  BackendStatus,
  CompareResponse,
  EnvironmentInfo,
  GridData,
  LoadEnvironmentResponse,
  MissionResult,
  SearchResult,
} from './types'

export class ApiRequestError extends Error {
  code: string
  details?: unknown
  status: number

  constructor(status: number, error: ApiError) {
    super(error.message)
    this.name = 'ApiRequestError'
    this.status = status
    this.code = error.code
    this.details = error.details
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = (data as { error?: ApiError }).error ?? {
      code: 'HTTP_ERROR',
      message: res.statusText || 'Request failed',
    }
    throw new ApiRequestError(res.status, err)
  }
  return data as T
}

export const api = {
  health: () => request<{ status: string }>('/api/health'),
  backendStatus: () => request<BackendStatus>('/api/backend-status'),
  environments: () => request<EnvironmentInfo[]>('/api/environments'),
  loadEnvironment: (body: { name?: string; text?: string }) =>
    request<LoadEnvironmentResponse>('/api/environment/load', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  saveEnvironment: (grid: GridData) =>
    request<{ text: string }>('/api/environment/save', {
      method: 'POST',
      body: JSON.stringify({ grid }),
    }),
  search: (body: {
    envText: string
    start: [number, number]
    goal: [number, number]
    algorithm: string
  }) =>
    request<SearchResult>('/api/search', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  compare: (body: {
    envText: string
    pairs?: [number, number][][]
    algorithms?: string[]
  }) =>
    request<CompareResponse>('/api/compare', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  generateSchedule: (body: { envText: string; scheduleText: string }) =>
    request<{
      schedule: string[] | null
      assignment: Record<string, string> | null
      message: string
      constraintsChecked: string[]
    }>('/api/schedule/generate', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  executeMission: (body: {
    envText: string
    schedule: string[]
    algorithm: string
    scheduleSource: 'csp' | 'manual'
  }) =>
    request<MissionResult>('/api/mission/execute', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
}
