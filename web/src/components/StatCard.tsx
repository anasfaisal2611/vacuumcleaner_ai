import { CountUp } from './CountUp'
import { GlassCard } from './GlassCard'

export function StatCard({
  label,
  value,
  suffix = '',
  decimals = 0,
  accent,
}: {
  label: string
  value: number | null | undefined
  suffix?: string
  decimals?: number
  accent?: string
}) {
  return (
    <GlassCard className="!rounded-2xl !p-4">
      <div
        className="font-display text-3xl font-bold"
        style={{ color: accent ?? 'var(--primary)' }}
      >
        <CountUp value={value} suffix={suffix} decimals={decimals} />
      </div>
      <div className="mt-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">
        {label}
      </div>
    </GlassCard>
  )
}
