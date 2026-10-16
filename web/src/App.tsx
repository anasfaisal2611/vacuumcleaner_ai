import { AnimatePresence, motion } from 'framer-motion'
import { useEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { Splash } from './components/Splash'
import { ToastHost } from './components/Toast'
import { AboutPage } from './pages/AboutPage'
import { ComparePage } from './pages/ComparePage'
import { EnvironmentPage } from './pages/EnvironmentPage'
import { MissionPage } from './pages/MissionPage'
import { SearchLabPage } from './pages/SearchLabPage'
import { useAppStore } from './store'

export default function App() {
  const location = useLocation()
  const splashDone = useAppStore((s) => s.splashDone)
  const refreshBackend = useAppStore((s) => s.refreshBackend)
  const setSidebarOpen = useAppStore((s) => s.setSidebarOpen)

  useEffect(() => {
    void refreshBackend()
    const mq = window.matchMedia('(min-width: 768px)')
    const sync = () => setSidebarOpen(mq.matches)
    sync()
    mq.addEventListener('change', sync)
    return () => mq.removeEventListener('change', sync)
  }, [refreshBackend, setSidebarOpen])

  return (
    <>
      <div className="aurora-bg" aria-hidden>
        <div className="aurora-blob a" />
        <div className="aurora-blob b" />
        <div className="aurora-blob c" />
        <div className="noise" />
        <div className="grid-overlay" />
      </div>

      <Splash />

      {splashDone ? (
        <div className="flex min-h-screen md:gap-0">
          <Sidebar />
          <main className="flex min-h-screen flex-1 flex-col p-3 pt-14 md:p-3 md:pt-3">
            <div className="glass flex min-h-[calc(100vh-1.5rem)] flex-1 flex-col overflow-hidden p-4 md:p-5">
              <AnimatePresence mode="wait">
                <motion.div
                  key={location.pathname}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.25 }}
                  className="flex h-full min-h-0 flex-1 flex-col"
                >
                  <Routes location={location}>
                    <Route path="/" element={<EnvironmentPage />} />
                    <Route path="/search" element={<SearchLabPage />} />
                    <Route path="/mission" element={<MissionPage />} />
                    <Route path="/compare" element={<ComparePage />} />
                    <Route path="/about" element={<AboutPage />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </motion.div>
              </AnimatePresence>
            </div>
          </main>
        </div>
      ) : null}

      <ToastHost />
    </>
  )
}
