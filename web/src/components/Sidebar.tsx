import { AnimatePresence, motion } from 'framer-motion'
import {
  FlaskConical,
  GitCompare,
  Info,
  LayoutGrid,
  Map,
  Menu,
  Moon,
  Sun,
  X,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { APP_NAME } from '../data/team'
import { useAppStore } from '../store'

const NAV = [
  { to: '/', label: 'Environment', icon: Map },
  { to: '/search', label: 'Search Lab', icon: FlaskConical },
  { to: '/mission', label: 'Full Mission', icon: LayoutGrid },
  { to: '/compare', label: 'Compare', icon: GitCompare },
  { to: '/about', label: 'About', icon: Info },
]

export function Sidebar() {
  const open = useAppStore((s) => s.sidebarOpen)
  const setOpen = useAppStore((s) => s.setSidebarOpen)
  const theme = useAppStore((s) => s.theme)
  const toggleTheme = useAppStore((s) => s.toggleTheme)
  const backend = useAppStore((s) => s.backend)
  const envName = useAppStore((s) => s.envName)

  return (
    <>
      <button
        type="button"
        className="glass fixed left-3 top-3 z-50 flex h-10 w-10 items-center justify-center rounded-xl md:hidden"
        aria-label="Toggle navigation"
        onClick={() => setOpen(!open)}
      >
        {open ? <X size={18} /> : <Menu size={18} />}
      </button>

      <AnimatePresence>
        {open ? (
          <motion.aside
            initial={{ x: -24, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -24, opacity: 0 }}
            className="glass fixed inset-y-3 left-3 z-40 flex w-[240px] flex-col p-4 md:static md:z-auto md:m-3 md:h-[calc(100vh-1.5rem)]"
          >
            <div className="mb-6 flex items-center gap-3 px-1">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-400 to-cyan-600 shadow-[0_0_20px_rgba(45,212,191,0.35)]">
                <span className="text-lg font-bold text-slate-950">S</span>
              </div>
              <div>
                <div className="font-display text-lg font-bold leading-none">
                  {APP_NAME}
                </div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.18em] text-[var(--text-muted)]">
                  AI Vacuum
                </div>
              </div>
            </div>

            <nav className="relative flex flex-1 flex-col gap-1">
              {NAV.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) =>
                    `relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                      isActive
                        ? 'text-teal-300'
                        : 'text-[var(--text-muted)] hover:bg-white/5 hover:text-[var(--text)]'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      {isActive ? (
                        <motion.span
                          layoutId="nav-pill"
                          className="absolute inset-0 rounded-xl border border-teal-400/25 bg-teal-400/10"
                          transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                        />
                      ) : null}
                      <Icon size={16} className="relative z-10" />
                      <span className="relative z-10">{label}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </nav>

            <div className="mt-4 space-y-3 border-t border-[var(--border)] pt-4">
              <div className="rounded-xl bg-white/5 px-3 py-2 text-xs text-[var(--text-muted)]">
                Env:{' '}
                <span className="font-medium text-[var(--text)]">
                  {envName || 'none'}
                </span>
              </div>
              <div className="flex gap-2">
                <Chip ok={!!backend?.csp} label="CSP" />
                <Chip ok={!!backend?.integration} label="Integration" />
              </div>
              <button
                type="button"
                onClick={toggleTheme}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--border)] bg-white/5 px-3 py-2 text-sm hover:bg-white/10"
                aria-label="Toggle theme"
              >
                {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
                {theme === 'dark' ? 'Light' : 'Dark'}
              </button>
            </div>
          </motion.aside>
        ) : null}
      </AnimatePresence>
    </>
  )
}

function Chip({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={`flex-1 rounded-lg px-2 py-1.5 text-center text-[11px] font-semibold ${
        ok
          ? 'bg-emerald-400/15 text-emerald-300'
          : 'bg-amber-400/15 text-amber-300'
      }`}
    >
      {label}
    </span>
  )
}
