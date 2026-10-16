import { useEffect, useRef } from 'react'

/** Single rAF loop; calls `onTick(dtSeconds)` while `running` is true. */
export function useAnimationClock(
  running: boolean,
  onTick: (dt: number) => void,
): void {
  const tickRef = useRef(onTick)
  tickRef.current = onTick

  useEffect(() => {
    if (!running) return
    let raf = 0
    let last = performance.now()
    const loop = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000)
      last = now
      tickRef.current(dt)
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [running])
}
