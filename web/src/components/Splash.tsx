import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { APP_NAME, TAGLINE } from '../data/team'
import { useReducedMotion } from '../hooks/useReducedMotion'
import { useAppStore } from '../store'

export function Splash() {
  const done = useAppStore((s) => s.splashDone)
  const setDone = useAppStore((s) => s.setSplashDone)
  const reduced = useReducedMotion()
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (sessionStorage.getItem('safaye-splash') === '1') {
      setDone()
      return
    }
    if (reduced) {
      sessionStorage.setItem('safaye-splash', '1')
      setDone()
      return
    }
    const start = performance.now()
    let raf = 0
    const loop = (now: number) => {
      const t = Math.min(1, (now - start) / 2000)
      setProgress(t)
      if (t < 1) raf = requestAnimationFrame(loop)
      else {
        sessionStorage.setItem('safaye-splash', '1')
        setTimeout(setDone, 280)
      }
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [reduced, setDone])

  useEffect(() => {
    const skip = () => {
      sessionStorage.setItem('safaye-splash', '1')
      setDone()
    }
    window.addEventListener('keydown', skip)
    window.addEventListener('click', skip)
    return () => {
      window.removeEventListener('keydown', skip)
      window.removeEventListener('click', skip)
    }
  }, [setDone])

  return (
    <AnimatePresence>
      {!done ? (
        <motion.div
          className="fixed inset-0 z-[100] flex flex-col items-center justify-center overflow-hidden bg-[#070b14]"
          exit={{ opacity: 0 }}
          transition={{ duration: 0.45 }}
        >
          <div className="aurora-blob a opacity-40" />
          <div className="aurora-blob b opacity-30" />
          <div className="relative mb-8 h-16 w-[min(720px,90vw)]">
            <motion.div
              className="absolute inset-y-3 left-0 rounded-full bg-white/10"
              style={{ width: `${progress * 100}%` }}
            />
            <motion.div
              className="absolute top-1/2 -translate-y-1/2"
              style={{ left: `calc(${progress * 100}% - 18px)` }}
            >
              <RobotLogo />
            </motion.div>
          </div>
          <motion.h1
            className="font-display text-5xl font-bold tracking-tight text-white md:text-6xl"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: Math.min(1, progress * 1.6), y: 0 }}
          >
            {APP_NAME}
          </motion.h1>
          <p className="mt-3 text-sm text-slate-400">{TAGLINE}</p>
          <div className="mt-10 h-1.5 w-48 overflow-hidden rounded-full bg-white/10">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-teal-400 to-cyan-300"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
          <p className="mt-4 text-xs text-slate-500">Click or press any key to skip</p>
        </motion.div>
      ) : null}
    </AnimatePresence>
  )
}

function RobotLogo() {
  return (
    <svg width="36" height="36" viewBox="0 0 36 36" aria-hidden>
      <defs>
        <radialGradient id="rg" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#99f6e4" />
          <stop offset="100%" stopColor="#0d9488" />
        </radialGradient>
      </defs>
      <ellipse cx="18" cy="18" rx="14" ry="12" fill="url(#rg)" />
      <circle cx="24" cy="16" r="3.2" fill="#ecfeff" />
      <circle cx="24" cy="16" r="1.4" fill="#0f172a" />
    </svg>
  )
}
