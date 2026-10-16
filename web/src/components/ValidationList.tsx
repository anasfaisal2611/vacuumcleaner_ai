import { motion } from 'framer-motion'
import { Check, X } from 'lucide-react'
import type { ValidationItem } from '../types'

export function ValidationList({ items }: { items: ValidationItem[] }) {
  return (
    <ul className="space-y-2">
      {items.map((item, i) => (
        <motion.li
          key={item.rule}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.05 }}
          className="flex items-start gap-2 rounded-xl bg-white/5 px-3 py-2 text-sm"
        >
          <span
            className={`mt-0.5 flex h-5 w-5 items-center justify-center rounded-full ${
              item.ok ? 'bg-emerald-400/20 text-emerald-300' : 'bg-rose-400/20 text-rose-300'
            }`}
          >
            {item.ok ? <Check size={12} /> : <X size={12} />}
          </span>
          <span>
            <span className="font-medium">{item.rule.replaceAll('_', ' ')}</span>
            <span className="mt-0.5 block text-xs text-[var(--text-muted)]">
              {item.message}
            </span>
          </span>
        </motion.li>
      ))}
    </ul>
  )
}
