export type Pos = [number, number]

export interface DirtyCell {
  label: string
  pos: Pos
}

export interface GridData {
  rows: number
  cols: number
  obstacles: Pos[]
  dirty: DirtyCell[]
  station: Pos
}

export interface ValidationItem {
  rule: string
  ok: boolean
  message: string
}

export interface LoadEnvironmentResponse {
  grid: GridData
  validation: ValidationItem[]
  unreachable: string[]
  rawText: string
}

export interface EnvironmentInfo {
  name: string
  label: string
}

export interface BackendStatus {
  csp: boolean
  integration: boolean
  missing: string[]
}

export interface SearchResult {
  algorithm: string
  found: boolean
  path: Pos[] | null
  cost: number | null
  nodesExpanded: number
  expandedOrder: Pos[]
  frontierMaxSize: number
  runtimeMs: number
  message: string
}

export interface CompareRow {
  pair: string
  algorithm: string
  found: boolean
  cost: number | null
  nodesExpanded: number
  frontierMaxSize: number
  runtimeMs: number
}

export interface CompareResponse {
  rows: CompareRow[]
  insight: string
  totals: Record<string, unknown>
}

export interface MissionLeg {
  from: Pos
  to: Pos
  fromLabel: string
  toLabel: string
  path: Pos[] | null
  cost: number | null
  nodesExpanded: number
  expandedOrder: Pos[]
}

export interface MissionResult {
  completePath: Pos[]
  totalCost: number
  totalMovements: number
  success: boolean
  legs: MissionLeg[]
  message: string
  scheduleSource: string
}

export interface ApiError {
  code: string
  message: string
  details?: unknown
}

export type ThemeMode = 'dark' | 'light'
export type ToastKind = 'info' | 'success' | 'error' | 'warning'

export interface ToastItem {
  id: string
  message: string
  kind: ToastKind
}
