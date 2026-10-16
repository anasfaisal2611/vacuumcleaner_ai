import { useMemo, useState } from 'react'
import { ApiRequestError, api } from '../api'
import { BarChart } from '../components/BarChart'
import { GlassCard } from '../components/GlassCard'
import { GradientButton } from '../components/GradientButton'
import { generateInsight } from '../lib/insight'
import { rowsToCsv } from '../lib/csv'
import { useAppStore } from '../store'
import type { CompareRow } from '../types'

export function ComparePage() {
  const rawText = useAppStore((s) => s.rawText)
  const pushToast = useAppStore((s) => s.pushToast)
  const [rows, setRows] = useState<CompareRow[]>([])
  const [insight, setInsight] = useState('')
  const [loading, setLoading] = useState(false)
  const [sortKey, setSortKey] = useState<keyof CompareRow>('pair')

  const sorted = useMemo(() => {
    return [...rows].sort((a, b) => String(a[sortKey]).localeCompare(String(b[sortKey])))
  }, [rows, sortKey])

  async function run() {
    if (!rawText) {
      pushToast('Load an environment first', 'warning')
      return
    }
    setLoading(true)
    try {
      const res = await api.compare({ envText: rawText })
      setRows(res.rows)
      setInsight(res.insight || generateInsight(res.rows))
      pushToast(`Compared ${res.rows.length} rows`, 'success')
    } catch (e) {
      pushToast(e instanceof ApiRequestError ? e.message : 'Compare failed', 'error')
    } finally {
      setLoading(false)
    }
  }

  function exportCsv() {
    const blob = new Blob([rowsToCsv(rows)], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'comparison.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  async function copyText() {
    const text = rows
      .map(
        (r) =>
          `${r.pair} | ${r.algorithm} | ${r.cost ?? '—'} | ${r.nodesExpanded} | ${r.frontierMaxSize} | ${r.runtimeMs.toFixed(2)}`,
      )
      .join('\n')
    await navigator.clipboard.writeText(text)
    pushToast('Copied table', 'success')
  }

  const bfsNodes = mean(rows.filter((r) => r.algorithm === 'bfs' && r.found).map((r) => r.nodesExpanded))
  const astarNodes = mean(
    rows.filter((r) => r.algorithm === 'astar' && r.found).map((r) => r.nodesExpanded),
  )
  const bfsCost = mean(rows.filter((r) => r.algorithm === 'bfs' && r.found).map((r) => r.cost ?? 0))
  const astarCost = mean(
    rows.filter((r) => r.algorithm === 'astar' && r.found).map((r) => r.cost ?? 0),
  )

  return (
    <div className="flex h-full flex-col gap-4 overflow-auto">
      <div className="flex flex-wrap gap-2">
        <GradientButton type="button" onClick={run} disabled={loading}>
          {loading ? 'Running…' : 'Run comparison'}
        </GradientButton>
        <GradientButton type="button" variant="ghost" onClick={exportCsv} disabled={!rows.length}>
          Export CSV
        </GradientButton>
        <GradientButton type="button" variant="ghost" onClick={copyText} disabled={!rows.length}>
          Copy as text
        </GradientButton>
      </div>

      <GlassCard>
        <div className="overflow-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="text-[11px] uppercase tracking-wider text-[var(--text-muted)]">
              <tr>
                {(
                  [
                    ['pair', 'Pair'],
                    ['algorithm', 'Algorithm'],
                    ['cost', 'Cost'],
                    ['nodesExpanded', 'Nodes'],
                    ['frontierMaxSize', 'Frontier'],
                    ['runtimeMs', 'Time (ms)'],
                  ] as const
                ).map(([k, label]) => (
                  <th key={k} className="cursor-pointer px-2 py-2" onClick={() => setSortKey(k)}>
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((r, i) => (
                <tr key={`${r.pair}-${r.algorithm}-${i}`} className="border-t border-[var(--border)]">
                  <td className="px-2 py-2">{r.pair}</td>
                  <td className="px-2 py-2 uppercase">{r.algorithm}</td>
                  <td className="tabular px-2 py-2">{r.found ? r.cost : '—'}</td>
                  <td className="tabular px-2 py-2">{r.nodesExpanded}</td>
                  <td className="tabular px-2 py-2">{r.frontierMaxSize}</td>
                  <td className="tabular px-2 py-2">{r.runtimeMs.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.length ? (
            <p className="py-8 text-center text-sm text-[var(--text-muted)]">
              Run a comparison to populate the table.
            </p>
          ) : null}
        </div>
      </GlassCard>

      <div className="grid gap-4 md:grid-cols-2">
        <BarChart
          title="Avg nodes expanded"
          labels={['Average']}
          series={[
            { name: 'BFS', values: [bfsNodes], color: '#38bdf8' },
            { name: 'A*', values: [astarNodes], color: '#e879f9' },
          ]}
        />
        <BarChart
          title="Avg path cost"
          labels={['Average']}
          series={[
            { name: 'BFS', values: [bfsCost], color: '#38bdf8' },
            { name: 'A*', values: [astarCost], color: '#e879f9' },
          ]}
        />
      </div>

      <GlassCard title="Insight">
        <p className="text-sm leading-relaxed text-[var(--text-muted)]">
          {insight || 'Insights appear after a comparison run.'}
        </p>
      </GlassCard>
    </div>
  )
}

function mean(xs: number[]) {
  return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0
}
