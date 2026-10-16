import { describe, expect, it } from 'vitest'
import { rowsToCsv } from './csv'

describe('rowsToCsv', () => {
  it('escapes commas in pair labels', () => {
    const csv = rowsToCsv([
      {
        pair: 'C → D1, east',
        algorithm: 'bfs',
        found: true,
        cost: 7,
        nodesExpanded: 10,
        frontierMaxSize: 4,
        runtimeMs: 1.234,
      },
    ])
    expect(csv.split('\n')[0]).toContain('Pair,Algorithm')
    expect(csv).toContain('"C → D1, east"')
  })
})
