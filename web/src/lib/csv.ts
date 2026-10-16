import type { CompareRow } from '../types'

/** Serialize comparison rows to CSV text. */
export function rowsToCsv(rows: CompareRow[]): string {
  const header =
    'Pair,Algorithm,Found,Cost,Nodes expanded,Max frontier,Time (ms)'
  const lines = rows.map((r) =>
    [
      csvEscape(r.pair),
      r.algorithm,
      String(r.found),
      r.cost ?? '',
      r.nodesExpanded,
      r.frontierMaxSize,
      r.runtimeMs.toFixed(2),
    ].join(','),
  )
  return [header, ...lines].join('\n')
}

function csvEscape(value: string): string {
  if (/[",\n]/.test(value)) return `"${value.replace(/"/g, '""')}"`
  return value
}
