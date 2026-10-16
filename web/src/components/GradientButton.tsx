import { motion } from 'framer-motion'
import type { ReactNode } from 'react'

export function GradientButton({
  children,
  className = '',
  variant = 'primary',
  disabled,
  type = 'button',
  onClick,
  'aria-label': ariaLabel,
}: {
  children: ReactNode
  className?: string
  variant?: 'primary' | 'ghost' | 'danger'
  disabled?: boolean
  type?: 'button' | 'submit' | 'reset'
  onClick?: () => void
  'aria-label'?: string
}) {
  const base =
    'relative inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition focus-visible:outline-none disabled:opacity-50'
  const styles =
    variant === 'primary'
      ? 'text-slate-950 bg-gradient-to-r from-teal-400 via-cyan-300 to-teal-400 bg-[length:200%_100%] shadow-[0_0_24px_rgba(45,212,191,0.35)]'
      : variant === 'danger'
        ? 'bg-rose-500/15 text-rose-300 border border-rose-400/30'
        : 'bg-white/5 text-[var(--text)] border border-[var(--border)] hover:bg-white/10'

  return (
    <motion.button
      type={type}
      disabled={disabled}
      aria-label={ariaLabel}
      onClick={onClick}
      whileHover={{ scale: disabled ? 1 : 1.03 }}
      whileTap={{ scale: disabled ? 1 : 0.97 }}
      className={`${base} ${styles} ${className}`}
    >
      {variant === 'primary' ? (
        <span className="pointer-events-none absolute inset-0 rounded-xl opacity-40 [background:linear-gradient(110deg,transparent,rgba(255,255,255,0.45),transparent)] bg-[length:200%_100%] animate-[shimmer_2.4s_linear_infinite]" />
      ) : null}
      <span className="relative z-10">{children}</span>
    </motion.button>
  )
}
