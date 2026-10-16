import { motion } from 'framer-motion'
import { APP_NAME, COURSE, INSTITUTION, TAGLINE, TEAM } from '../data/team'
import { GlassCard } from '../components/GlassCard'

const FLOW = ['Schedule.txt', 'CSP', 'Graph Search', 'Solution']

export function AboutPage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5 overflow-auto pb-8">
      <div>
        <h1 className="font-display text-4xl font-bold text-teal-300">{APP_NAME}</h1>
        <p className="mt-2 text-[var(--text-muted)]">{TAGLINE}</p>
      </div>

      <GlassCard title="Course">
        <p className="font-medium">{COURSE}</p>
        <p className="mt-1 text-sm text-[var(--text-muted)]">{INSTITUTION}</p>
      </GlassCard>

      <GlassCard title="How it works">
        <div className="flex flex-wrap items-center gap-2">
          {FLOW.map((step, i) => (
            <motion.div
              key={step}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.12 }}
              className="flex items-center gap-2"
            >
              <span className="rounded-xl border border-teal-400/30 bg-teal-400/10 px-3 py-2 text-sm font-semibold text-teal-200">
                {step}
              </span>
              {i < FLOW.length - 1 ? (
                <span className="text-[var(--text-muted)]">→</span>
              ) : null}
            </motion.div>
          ))}
        </div>
        <p className="mt-4 text-sm leading-relaxed text-[var(--text-muted)]">
          Member 2’s CSP produces a cleaning order from Schedule.txt. Member 1’s BFS/A*
          finds paths between waypoints. Member 3 integrates the full mission back to the
          station. This GUI never invents CSP results.
        </p>
      </GlassCard>

      <GlassCard title="Team">
        <ul className="space-y-3">
          {TEAM.map((m) => (
            <li key={m.name} className="rounded-xl bg-white/5 px-3 py-2">
              <div className="font-semibold">
                {m.name}{' '}
                <span className="text-sm font-normal text-[var(--text-muted)]">{m.roll}</span>
              </div>
              <div className="text-xs text-[var(--text-muted)]">{m.role}</div>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-[var(--text-muted)]">
          Edit names in <code>web/src/data/team.ts</code>.
        </p>
      </GlassCard>
    </div>
  )
}
