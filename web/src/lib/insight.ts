import type { CompareRow } from '../types'

/** Auto-generate insight text from comparison rows (not hardcoded). */
export function generateInsight(rows: CompareRow[]): string {
  const byPair = new Map<string, Record<string, CompareRow>>()
  for (const r of rows) {
    const bucket = byPair.get(r.pair) ?? {}
    bucket[r.algorithm] = r
    byPair.set(r.pair, bucket)
  }

  let equalCost = 0
  let fewerAstar = 0
  let tieExpand = 0
  let total = 0
  let bfsNodes = 0
  let astarNodes = 0
  const failures = rows.filter((r) => !r.found).length

  for (const algos of byPair.values()) {
    const b = algos.bfs
    const a = algos.astar
    if (!b || !a || !b.found || !a.found) continue
    total += 1
    bfsNodes += b.nodesExpanded
    astarNodes += a.nodesExpanded
    if (b.cost === a.cost) equalCost += 1
    if (a.nodesExpanded < b.nodesExpanded) fewerAstar += 1
    else if (a.nodesExpanded === b.nodesExpanded) tieExpand += 1
  }

  if (total === 0) {
    if (failures) {
      return `No comparable successful pairs (${failures} failed row(s)). Check unreachable goals or obstacles.`
    }
    return 'No comparable successful pairs.'
  }

  const pct = bfsNodes === 0 ? 0 : (100 * (bfsNodes - astarNodes)) / bfsNodes
  const parts = [
    `Across ${total} successful pair(s), BFS and A* agreed on cost in ${equalCost}/${total} case(s).`,
  ]
  if (pct > 0.5) {
    parts.push(
      `A* expanded ${pct.toFixed(0)}% fewer nodes overall (${astarNodes} vs ${bfsNodes}).`,
    )
  } else if (pct < -0.5) {
    parts.push(
      `BFS expanded fewer nodes overall (${bfsNodes} vs ${astarNodes}).`,
    )
  } else {
    parts.push(
      `Node expansions were essentially tied (${astarNodes} vs ${bfsNodes}; ${tieExpand} per-pair ties).`,
    )
  }
  parts.push(`A* expanded fewer nodes on ${fewerAstar}/${total} pair(s).`)
  if (failures) parts.push(`${failures} row(s) reported no path.`)
  return parts.join(' ')
}
