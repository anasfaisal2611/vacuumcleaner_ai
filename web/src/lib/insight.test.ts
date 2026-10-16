import { describe, expect, it } from 'vitest'
import { generateInsight } from './insight'
import type { CompareRow } from '../types'

function row(
  pair: string,
  algorithm: string,
  found: boolean,
  cost: number | null,
  nodes: number,
): CompareRow {
  return {
    pair,
    algorithm,
    found,
    cost,
    nodesExpanded: nodes,
    frontierMaxSize: 0,
    runtimeMs: 1,
  }
}

describe('generateInsight', () => {
  it('reports A* fewer nodes with equal cost', () => {
    const text = generateInsight([
      row('C → D1', 'bfs', true, 10, 40),
      row('C → D1', 'astar', true, 10, 20),
    ])
    expect(text).toContain('agreed on cost')
    expect(text).toMatch(/50% fewer/)
  })

  it('handles expansion ties', () => {
    const text = generateInsight([
      row('C → D1', 'bfs', true, 5, 12),
      row('C → D1', 'astar', true, 5, 12),
    ])
    expect(text).toContain('tied')
  })

  it('handles failures', () => {
    const text = generateInsight([
      row('C → D4', 'bfs', false, null, 8),
      row('C → D4', 'astar', false, null, 8),
    ])
    expect(text).toMatch(/failed|No comparable/i)
  })
})
