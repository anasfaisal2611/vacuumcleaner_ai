import { describe, expect, it } from 'vitest'
import { easeInOutCubic, easeOutCubic, lerp } from './easing'

describe('easing', () => {
  it('easeOutCubic endpoints', () => {
    expect(easeOutCubic(0)).toBe(0)
    expect(easeOutCubic(1)).toBe(1)
    expect(easeOutCubic(0.5)).toBeGreaterThan(0.5)
  })

  it('easeInOutCubic midpoint', () => {
    expect(easeInOutCubic(0.5)).toBeCloseTo(0.5, 5)
  })

  it('lerp', () => {
    expect(lerp(0, 10, 0.5)).toBe(5)
  })
})
