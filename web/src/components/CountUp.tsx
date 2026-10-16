import { animate, useMotionValue, useMotionValueEvent } from 'framer-motion'
import { useEffect, useState } from 'react'
import { useReducedMotion } from '../hooks/useReducedMotion'

export function CountUp({
  value,
  suffix = '',
  decimals = 0,
  className = '',
}: {
  value: number | null | undefined
  suffix?: string
  decimals?: number
  className?: string
}) {
  const reduced = useReducedMotion()
  const mv = useMotionValue(0)
  const [display, setDisplay] = useState('—')

  useMotionValueEvent(mv, 'change', (v) => {
    setDisplay(decimals > 0 ? v.toFixed(decimals) : String(Math.round(v)))
  })

  useEffect(() => {
    if (value == null || Number.isNaN(value)) {
      setDisplay('—')
      return
    }
    if (reduced) {
      setDisplay(decimals > 0 ? value.toFixed(decimals) : String(Math.round(value)))
      return
    }
    const ctrl = animate(mv, value, { duration: 0.7, ease: [0.22, 1, 0.36, 1] })
    return () => ctrl.stop()
  }, [value, decimals, mv, reduced])

  return (
    <span className={`tabular ${className}`}>
      {display}
      {value != null ? suffix : ''}
    </span>
  )
}
