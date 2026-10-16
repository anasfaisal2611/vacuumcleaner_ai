import { create } from 'zustand'
import { api } from './api'
import type {
  BackendStatus,
  GridData,
  LoadEnvironmentResponse,
  SearchResult,
  ThemeMode,
  ToastItem,
  ToastKind,
  ValidationItem,
} from './types'

interface AppState {
  theme: ThemeMode
  splashDone: boolean
  sidebarOpen: boolean
  backend: BackendStatus | null
  grid: GridData | null
  rawText: string
  validation: ValidationItem[]
  unreachable: string[]
  envName: string
  searchResult: SearchResult | null
  searchResultB: SearchResult | null
  toasts: ToastItem[]
  setTheme: (t: ThemeMode) => void
  toggleTheme: () => void
  setSplashDone: () => void
  setSidebarOpen: (v: boolean) => void
  pushToast: (message: string, kind?: ToastKind) => void
  dismissToast: (id: string) => void
  refreshBackend: () => Promise<void>
  applyEnvironment: (res: LoadEnvironmentResponse, name?: string) => void
  setSearchResults: (a: SearchResult | null, b?: SearchResult | null) => void
  updateGrid: (grid: GridData) => void
}

function loadTheme(): ThemeMode {
  const saved = localStorage.getItem('safayewala-theme')
  return saved === 'light' ? 'light' : 'dark'
}

export const useAppStore = create<AppState>((set, get) => ({
  theme: loadTheme(),
  splashDone: false,
  sidebarOpen: true,
  backend: null,
  grid: null,
  rawText: '',
  validation: [],
  unreachable: [],
  envName: '',
  searchResult: null,
  searchResultB: null,
  toasts: [],

  setTheme: (t) => {
    localStorage.setItem('safayewala-theme', t)
    document.documentElement.classList.toggle('light', t === 'light')
    set({ theme: t })
  },
  toggleTheme: () => {
    const next = get().theme === 'dark' ? 'light' : 'dark'
    get().setTheme(next)
  },
  setSplashDone: () => set({ splashDone: true }),
  setSidebarOpen: (v) => set({ sidebarOpen: v }),
  pushToast: (message, kind = 'info') => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
    set((s) => ({ toasts: [...s.toasts, { id, message, kind }] }))
    window.setTimeout(() => get().dismissToast(id), 3800)
  },
  dismissToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
  refreshBackend: async () => {
    try {
      const backend = await api.backendStatus()
      set({ backend })
    } catch {
      /* ignore — banner will show unknowns */
    }
  },
  applyEnvironment: (res, name = '') => {
    set({
      grid: res.grid,
      rawText: res.rawText,
      validation: res.validation,
      unreachable: res.unreachable,
      envName: name,
      searchResult: null,
      searchResultB: null,
    })
  },
  setSearchResults: (a, b = null) => set({ searchResult: a, searchResultB: b }),
  updateGrid: (grid) => set({ grid }),
}))

// Apply theme on boot
document.documentElement.classList.toggle('light', loadTheme() === 'light')
