import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { useAppStore } from '../store'

const kindBorder: Record<string, string> = {
  info: 'border-l-teal-400',
  success: 'border-l-emerald-400',
  error: 'border-l-rose-400',
  warning: 'border-l-amber-400',
}

export function ToastHost() {
  const toasts = useAppStore((s) => s.toasts)
  const dismiss = useAppStore((s) => s.dismissToast)

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[80] flex w-[min(360px,calc(100vw-2rem))] flex-col gap-2">
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            initial={{ opacity: 0, x: 40, y: 8 }}
            animate={{ opacity: 1, x: 0, y: 0 }}
            exit={{ opacity: 0, x: 30 }}
            className={`pointer-events-auto glass border-l-4 px-4 py-3 ${kindBorder[t.kind]}`}
            role="status"
          >
            <div className="flex items-start gap-3">
              <p className="flex-1 text-sm">{t.message}</p>
              <button
                type="button"
                aria-label="Dismiss"
                className="rounded-md p-1 opacity-60 hover:opacity-100"
                onClick={() => dismiss(t.id)}
              >
                <X size={14} />
              </button>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
