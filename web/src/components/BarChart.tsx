import { motion } from 'framer-motion'

export function BarChart({
  title,
  labels,
  series,
}: {
  title: string
  labels: string[]
  series: { name: string; values: number[]; color: string }[]
}) {
  const max = Math.max(1, ...series.flatMap((s) => s.values))
  return (
    <div className="glass p-4">
      <h3 className="font-display mb-4 text-sm font-bold">{title}</h3>
      <div className="flex h-44 items-end gap-6">
        {labels.map((label, i) => (
          <div key={label} className="flex flex-1 flex-col items-center gap-2">
            <div className="flex h-36 w-full items-end justify-center gap-1">
              {series.map((s) => {
                const v = s.values[i] ?? 0
                const h = (v / max) * 100
                return (
                  <motion.div
                    key={s.name}
                    className="w-5 rounded-t-md"
                    style={{ background: s.color }}
                    initial={{ height: 0 }}
                    animate={{ height: `${h}%` }}
                    transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                    title={`${s.name}: ${v}`}
                  />
                )
              })}
            </div>
            <div className="truncate text-[10px] text-[var(--text-muted)]">{label}</div>
          </div>
        ))}
      </div>
      <div className="mt-3 flex gap-4 text-xs text-[var(--text-muted)]">
        {series.map((s) => (
          <span key={s.name} className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: s.color }} />
            {s.name}
          </span>
        ))}
      </div>
    </div>
  )
}
