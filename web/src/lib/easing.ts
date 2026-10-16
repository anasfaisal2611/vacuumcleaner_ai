/** Cubic ease-in-out in [0, 1]. */
export function easeInOutCubic(t: number): number {
  const x = Math.min(1, Math.max(0, t))
  return x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2
}

/** Cubic ease-out in [0, 1]. */
export function easeOutCubic(t: number): number {
  const x = Math.min(1, Math.max(0, t))
  return 1 - (1 - x) ** 3
}

/** Linear clamp. */
export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t
}
