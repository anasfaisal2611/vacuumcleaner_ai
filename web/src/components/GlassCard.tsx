import type { ReactNode } from 'react'
import { motion } from 'framer-motion'

export function GlassCard({
  title,
  children,
  className = '',
}: {
  title?: string
  children: ReactNode
  className?: string
}) {
  return (
    <motion.section
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`glass p-5 ${className}`}
    >
      {title ? (
        <h2 className="font-display mb-3 text-lg font-bold tracking-tight">
          {title}
        </h2>
      ) : null}
      {children}
    </motion.section>
  )
}
