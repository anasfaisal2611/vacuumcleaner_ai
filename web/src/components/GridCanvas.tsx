import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react'
import { easeInOutCubic, easeOutCubic } from '../lib/easing'
import type { GridData, Pos, SearchResult } from '../types'
import type { PlaybackApi } from './PlaybackBar'

export interface GridCanvasHandle extends PlaybackApi {
  loadSearch: (result: SearchResult, color?: string) => void
  loadMission: (path: Pos[], legPaths?: Pos[][], manual?: boolean) => void
}

type Mode = 'view' | 'search' | 'edit' | 'mission'

interface Props {
  grid: GridData | null
  mode?: Mode
  start?: Pos | null
  goal?: Pos | null
  onStartGoal?: (start: Pos | null, goal: Pos | null) => void
  onGridEdit?: (grid: GridData) => void
  onToast?: (message: string, kind?: 'error' | 'warning' | 'info') => void
  exploreColor?: string
  className?: string
}

interface Timeline {
  phase: 'idle' | 'explore' | 'path' | 'robot' | 'done'
  exploreIndex: number
  pathIndex: number
  robotI: number
  robotT: number
  cleaned: Set<string>
}

function key(p: Pos) {
  return `${p[0]},${p[1]}`
}

export const GridCanvas = forwardRef<GridCanvasHandle, Props>(function GridCanvas(
  {
    grid,
    mode = 'view',
    start = null,
    goal = null,
    onStartGoal,
    onGridEdit,
    onToast,
    exploreColor = '#38bdf8',
    className = '',
  },
  ref,
) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [hover, setHover] = useState<Pos | null>(null)
  const [manualBadge, setManualBadge] = useState(false)

  const resultRef = useRef<SearchResult | null>(null)
  const pathRef = useRef<Pos[]>([])
  const legsRef = useRef<Pos[][]>([])
  const colorRef = useRef(exploreColor)
  const exploredRef = useRef<Map<string, number>>(new Map())
  const obstaclePopRef = useRef<Map<string, number>>(new Map())
  const robotRef = useRef({ x: 0, y: 0, angle: 0, brush: 0 })
  const trailRef = useRef<{ x: number; y: number; a: number }[]>([])
  const particlesRef = useRef<
    { x: number; y: number; vx: number; vy: number; life: number; color: string }[]
  >([])
  const timelineRef = useRef<Timeline>({
    phase: 'idle',
    exploreIndex: 0,
    pathIndex: 0,
    robotI: 0,
    robotT: 0,
    cleaned: new Set(),
  })
  const layoutRef = useRef({ cell: 32, ox: 0, oy: 0, dpr: 1 })
  const tRef = useRef(0)
  const editPaintRef = useRef<boolean | null>(null)

  const obstacleSet = useMemo(
    () => new Set((grid?.obstacles ?? []).map((p) => key(p))),
    [grid],
  )

  useEffect(() => {
    if (!grid) return
    const map = new Map<string, number>()
    ;[...grid.obstacles]
      .sort((a, b) => a[0] - b[0] || a[1] - b[1])
      .forEach((p, i) => map.set(key(p), -0.04 * i))
    obstaclePopRef.current = map
    robotRef.current = {
      x: grid.station[1],
      y: grid.station[0],
      angle: 0,
      brush: 0,
    }
  }, [grid])

  const cellCenter = useCallback((pos: Pos) => {
    const { cell, ox, oy } = layoutRef.current
    return { x: ox + (pos[1] + 0.5) * cell, y: oy + (pos[0] + 0.5) * cell }
  }, [])

  const posAt = useCallback((x: number, y: number): Pos | null => {
    if (!grid) return null
    const { cell, ox, oy } = layoutRef.current
    const c = Math.floor((x - ox) / cell)
    const r = Math.floor((y - oy) / cell)
    if (r < 0 || c < 0 || r >= grid.rows || c >= grid.cols) return null
    return [r, c]
  }, [grid])

  const loadSearch = useCallback(
    (result: SearchResult, color?: string) => {
      resultRef.current = result
      pathRef.current = result.path ?? []
      legsRef.current = []
      colorRef.current = color ?? (result.algorithm === 'astar' ? '#e879f9' : '#38bdf8')
      exploredRef.current.clear()
      timelineRef.current = {
        phase: 'explore',
        exploreIndex: 0,
        pathIndex: 0,
        robotI: 0,
        robotT: 0,
        cleaned: new Set(),
      }
      setManualBadge(false)
      setPlaying(true)
      if (start) {
        const c = cellCenter(start)
        robotRef.current.x = c.x
        robotRef.current.y = c.y
      }
    },
    [cellCenter, start],
  )

  const loadMission = useCallback(
    (path: Pos[], legPaths: Pos[][] = [], manual = false) => {
      pathRef.current = path
      legsRef.current = legPaths
      resultRef.current = null
      exploredRef.current.clear()
      timelineRef.current = {
        phase: 'robot',
        exploreIndex: 0,
        pathIndex: path.length,
        robotI: 0,
        robotT: 0,
        cleaned: new Set(),
      }
      setManualBadge(manual)
      setPlaying(true)
      if (path[0]) {
        const c = cellCenter(path[0])
        robotRef.current.x = c.x
        robotRef.current.y = c.y
      }
    },
    [cellCenter],
  )

  const api: GridCanvasHandle = useMemo(
    () => ({
      playing,
      speed,
      play: () => setPlaying(true),
      pause: () => setPlaying(false),
      step: () => {
        setPlaying(false)
        advance(1)
      },
      reset: () => {
        timelineRef.current = {
          phase: 'idle',
          exploreIndex: 0,
          pathIndex: 0,
          robotI: 0,
          robotT: 0,
          cleaned: new Set(),
        }
        exploredRef.current.clear()
        trailRef.current = []
        particlesRef.current = []
        resultRef.current = null
        pathRef.current = []
        setPlaying(false)
        setManualBadge(false)
      },
      skip: () => {
        const order = resultRef.current?.expandedOrder ?? []
        order.forEach((p) => exploredRef.current.set(key(p), 0.55))
        timelineRef.current.exploreIndex = order.length
        timelineRef.current.pathIndex = pathRef.current.length
        timelineRef.current.robotI = Math.max(0, pathRef.current.length - 1)
        timelineRef.current.phase = 'done'
        if (pathRef.current.length) {
          const c = cellCenter(pathRef.current[pathRef.current.length - 1])
          robotRef.current.x = c.x
          robotRef.current.y = c.y
        }
        setPlaying(false)
      },
      setSpeed,
      loadSearch,
      loadMission,
    }),
    [playing, speed, loadSearch, loadMission, cellCenter],
  )

  useImperativeHandle(ref, () => api, [api])

  function advance(steps: number) {
    const tl = timelineRef.current
    const result = resultRef.current
    if (tl.phase === 'explore' && result) {
      tl.exploreIndex += steps
      while (
        exploredRef.current.size < Math.min(result.expandedOrder.length, Math.floor(tl.exploreIndex))
      ) {
        const pos = result.expandedOrder[exploredRef.current.size]
        exploredRef.current.set(key(pos), 0.85)
        const c = cellCenter(pos)
        particlesRef.current.push({
          x: c.x,
          y: c.y,
          vx: 0,
          vy: 0,
          life: 0.5,
          color: colorRef.current,
        })
      }
      if (exploredRef.current.size >= result.expandedOrder.length) {
        tl.phase = pathRef.current.length ? 'path' : 'done'
      }
    } else if (tl.phase === 'path') {
      tl.pathIndex += steps * 0.8
      if (tl.pathIndex >= pathRef.current.length) {
        tl.phase = 'robot'
        tl.robotI = 0
        tl.robotT = 0
      }
    } else if (tl.phase === 'robot' && pathRef.current.length > 1) {
      if (tl.robotI >= pathRef.current.length - 1) {
        tl.phase = 'done'
        setPlaying(false)
        return
      }
      tl.robotT += steps * 0.12
      const t = easeInOutCubic(Math.min(1, tl.robotT))
      const a = pathRef.current[tl.robotI]
      const b = pathRef.current[tl.robotI + 1]
      const ca = cellCenter(a)
      const cb = cellCenter(b)
      robotRef.current.x = ca.x + (cb.x - ca.x) * t
      robotRef.current.y = ca.y + (cb.y - ca.y) * t
      robotRef.current.angle = Math.atan2(cb.y - ca.y, cb.x - ca.x)
      trailRef.current.push({
        x: robotRef.current.x,
        y: robotRef.current.y,
        a: 0.7,
      })
      if (tl.robotT >= 1) {
        tl.robotI += 1
        tl.robotT = 0
        const arrived = pathRef.current[tl.robotI]
        const dirty = grid?.dirty.some(
          (d) => d.pos[0] === arrived[0] && d.pos[1] === arrived[1],
        )
        if (dirty && !tl.cleaned.has(key(arrived))) {
          tl.cleaned.add(key(arrived))
          const c = cellCenter(arrived)
          for (let i = 0; i < 12; i++) {
            const ang = Math.random() * Math.PI * 2
            const sp = 40 + Math.random() * 50
            particlesRef.current.push({
              x: c.x,
              y: c.y,
              vx: Math.cos(ang) * sp,
              vy: Math.sin(ang) * sp,
              life: 1,
              color: '#fbbf24',
            })
          }
        }
      }
    } else if (tl.phase === 'done') {
      setPlaying(false)
    }
  }

  // rAF draw loop
  useEffect(() => {
    let raf = 0
    let last = performance.now()
    const draw = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000) * speed
      last = now
      tRef.current += dt
      robotRef.current.brush += dt * 10

      obstaclePopRef.current.forEach((v, k) => {
        obstaclePopRef.current.set(k, Math.min(1, v + dt * 2.4))
      })
      exploredRef.current.forEach((v, k) => {
        exploredRef.current.set(k, Math.max(0.18, v - dt * 0.12))
      })
      trailRef.current = trailRef.current
        .map((p) => ({ ...p, a: p.a - dt * 1.4 }))
        .filter((p) => p.a > 0)
      particlesRef.current = particlesRef.current
        .map((p) => ({
          ...p,
          life: p.life - dt * 1.2,
          x: p.x + p.vx * dt,
          y: p.y + p.vy * dt,
          vx: p.vx * 0.96,
          vy: p.vy * 0.96,
        }))
        .filter((p) => p.life > 0)

      if (playing) advance(dt * 8)
      paint()
      raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, speed, grid, start, goal, hover, mode, manualBadge])

  function paint() {
    const canvas = canvasRef.current
    const wrap = wrapRef.current
    if (!canvas || !wrap) return
    const dpr = Math.min(2, window.devicePixelRatio || 1)
    const w = wrap.clientWidth
    const h = wrap.clientHeight
    if (canvas.width !== Math.floor(w * dpr) || canvas.height !== Math.floor(h * dpr)) {
      canvas.width = Math.floor(w * dpr)
      canvas.height = Math.floor(h * dpr)
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
    }
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, w, h)

    if (!grid) {
      ctx.fillStyle = 'rgba(148,163,184,0.7)'
      ctx.font = '14px Inter, sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText('Load an environment to begin', w / 2, h / 2)
      return
    }

    const pad = 16
    const cell = Math.min((w - pad * 2) / grid.cols, (h - pad * 2) / grid.rows)
    const ox = (w - cell * grid.cols) / 2
    const oy = (h - cell * grid.rows) / 2
    layoutRef.current = { cell, ox, oy, dpr }

    roundRect(ctx, ox - 8, oy - 8, cell * grid.cols + 16, cell * grid.rows + 16, 14)
    ctx.fillStyle = 'rgba(14,21,36,0.85)'
    ctx.fill()
    ctx.strokeStyle = 'rgba(148,163,184,0.2)'
    ctx.stroke()

    const dirtyMap = new Map(grid.dirty.map((d) => [key(d.pos), d.label]))
    const cleaned = timelineRef.current.cleaned

    for (let r = 0; r < grid.rows; r++) {
      for (let c = 0; c < grid.cols; c++) {
        const pos: Pos = [r, c]
        const k = key(pos)
        const x = ox + c * cell
        const y = oy + r * cell
        const isObs = obstacleSet.has(k)
        const isStation = grid.station[0] === r && grid.station[1] === c
        const dirtyLabel = dirtyMap.get(k)
        const isHover = hover && hover[0] === r && hover[1] === c

        if (isObs) {
          const pop = easeOutCubic(Math.max(0, obstaclePopRef.current.get(k) ?? 1))
          const hh = (cell - 4) * pop
          roundRect(ctx, x + 2, y + cell - 2 - hh, cell - 4, hh, 5)
          ctx.fillStyle = '#334155'
          ctx.fill()
          ctx.fillStyle = `rgba(100,116,139,${0.35 * pop})`
          roundRect(ctx, x + 4, y + cell - 2 - hh + 2, cell - 8, Math.max(2, hh * 0.35), 4)
          ctx.fill()
          continue
        }

        roundRect(ctx, x + 2, y + 2, cell - 4, cell - 4, 6)
        ctx.fillStyle = cleaned.has(k)
          ? '#12352f'
          : isHover
            ? '#243044'
            : '#1a2438'
        ctx.fill()
        ctx.strokeStyle = 'rgba(148,163,184,0.15)'
        ctx.stroke()

        if (isStation) {
          const pulse = 0.5 + 0.5 * Math.sin(tRef.current * 1.8)
          ctx.beginPath()
          ctx.arc(x + cell / 2, y + cell / 2, cell * 0.32, 0, Math.PI * 2)
          ctx.strokeStyle = `rgba(45,212,191,${0.45 + 0.4 * pulse})`
          ctx.lineWidth = 2
          ctx.stroke()
          ctx.fillStyle = '#5eead4'
          ctx.font = `bold ${Math.max(10, cell * 0.28)}px sans-serif`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText('⚡', x + cell / 2, y + cell / 2 + 1)
        } else if (dirtyLabel && !cleaned.has(k)) {
          for (let i = 0; i < 6; i++) {
            const ang = (i / 6) * Math.PI * 2 + tRef.current
            ctx.beginPath()
            ctx.arc(
              x + cell / 2 + Math.cos(ang) * cell * 0.15,
              y + cell / 2 + Math.sin(ang) * cell * 0.12,
              2 + (i % 2),
              0,
              Math.PI * 2,
            )
            ctx.fillStyle = i % 2 ? '#fbbf24' : '#f59e0b'
            ctx.globalAlpha = 0.7
            ctx.fill()
            ctx.globalAlpha = 1
          }
          roundRect(ctx, x + cell - cell * 0.42, y + 3, cell * 0.34, cell * 0.26, 4)
          ctx.fillStyle = '#f59e0b'
          ctx.fill()
          ctx.fillStyle = '#0f172a'
          ctx.font = `bold ${Math.max(8, cell * 0.18)}px Inter, sans-serif`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(dirtyLabel, x + cell - cell * 0.25, y + 3 + cell * 0.13)
        } else if (cleaned.has(k)) {
          ctx.strokeStyle = '#34d399'
          ctx.lineWidth = 2
          ctx.beginPath()
          ctx.moveTo(x + cell * 0.3, y + cell * 0.5)
          ctx.lineTo(x + cell * 0.45, y + cell * 0.65)
          ctx.lineTo(x + cell * 0.7, y + cell * 0.35)
          ctx.stroke()
        }
      }
    }

    // Explored overlays
    exploredRef.current.forEach((alpha, k) => {
      const [r, c] = k.split(',').map(Number) as Pos
      const x = ox + c * cell
      const y = oy + r * cell
      roundRect(ctx, x + 4, y + 4, cell - 8, cell - 8, 6)
      ctx.fillStyle = hexAlpha(colorRef.current, alpha)
      ctx.fill()
    })

    // Paths
    const drawPath = (path: Pos[], color: string, n?: number) => {
      if (path.length < 2) return
      const count = n ?? path.length
      ctx.strokeStyle = color
      ctx.lineWidth = Math.max(2, cell * 0.1)
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
      ctx.beginPath()
      for (let i = 0; i < Math.min(count, path.length); i++) {
        const p = cellCenter(path[i])
        if (i === 0) ctx.moveTo(p.x, p.y)
        else ctx.lineTo(p.x, p.y)
      }
      ctx.stroke()
    }

    if (legsRef.current.length) {
      const palette = ['#38bdf8', '#e879f9', '#f59e0b', '#2dd4bf', '#a78bfa', '#fb7185']
      legsRef.current.forEach((leg, i) => drawPath(leg, palette[i % palette.length]))
    } else if (pathRef.current.length && timelineRef.current.phase !== 'explore') {
      const n =
        timelineRef.current.phase === 'path'
          ? Math.floor(timelineRef.current.pathIndex)
          : pathRef.current.length
      drawPath(pathRef.current, '#5eead4', n)
    }

    // Start / goal
    const marker = (pos: Pos | null | undefined, color: string, label: string) => {
      if (!pos) return
      const c = cellCenter(pos)
      const pulse = 0.6 + 0.4 * Math.sin(tRef.current * 2)
      ctx.beginPath()
      ctx.arc(c.x, c.y, cell * 0.28, 0, Math.PI * 2)
      ctx.strokeStyle = color
      ctx.lineWidth = 2
      ctx.globalAlpha = 0.4 + 0.4 * pulse
      ctx.stroke()
      ctx.globalAlpha = 1
      ctx.fillStyle = color
      ctx.font = `bold ${Math.max(10, cell * 0.22)}px Inter`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(label, c.x, c.y)
    }
    if (mode === 'search' || start) marker(start, '#34d399', 'S')
    if (mode === 'search' || goal) marker(goal, '#f87171', 'G')

    // Trail + robot
    trailRef.current.forEach((p) => {
      ctx.beginPath()
      ctx.arc(p.x, p.y, 3.5, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(94,234,212,${p.a * 0.4})`
      ctx.fill()
    })
    particlesRef.current.forEach((p) => {
      ctx.beginPath()
      ctx.arc(p.x, p.y, 2.5, 0, Math.PI * 2)
      ctx.fillStyle = hexAlpha(p.color, p.life)
      ctx.fill()
    })

    const rx = robotRef.current.x
    const ry = robotRef.current.y
    const rr = Math.max(6, cell * 0.26)
    const grd = ctx.createRadialGradient(rx, ry, 0, rx, ry, rr * 1.8)
    grd.addColorStop(0, 'rgba(94,234,212,0.35)')
    grd.addColorStop(1, 'rgba(94,234,212,0)')
    ctx.fillStyle = grd
    ctx.beginPath()
    ctx.arc(rx, ry, rr * 1.6, 0, Math.PI * 2)
    ctx.fill()
    ctx.beginPath()
    ctx.ellipse(rx, ry, rr, rr * 0.85, 0, 0, Math.PI * 2)
    const body = ctx.createLinearGradient(rx - rr, ry - rr, rx + rr, ry + rr)
    body.addColorStop(0, '#99f6e4')
    body.addColorStop(1, '#0d9488')
    ctx.fillStyle = body
    ctx.fill()
    const eyeX = rx + Math.cos(robotRef.current.angle) * rr * 0.35
    const eyeY = ry + Math.sin(robotRef.current.angle) * rr * 0.35
    ctx.beginPath()
    ctx.arc(eyeX, eyeY, rr * 0.2, 0, Math.PI * 2)
    ctx.fillStyle = '#ecfeff'
    ctx.fill()
    ctx.beginPath()
    ctx.arc(eyeX, eyeY, rr * 0.09, 0, Math.PI * 2)
    ctx.fillStyle = '#0f172a'
    ctx.fill()
    ctx.strokeStyle = '#f59e0b'
    ctx.lineWidth = 2
    for (let i = 0; i < 3; i++) {
      const ang = robotRef.current.brush + (i * Math.PI * 2) / 3
      ctx.beginPath()
      ctx.moveTo(rx, ry)
      ctx.lineTo(rx + Math.cos(ang) * rr * 0.7, ry + Math.sin(ang) * rr * 0.55)
      ctx.stroke()
    }

    if (manualBadge) {
      roundRect(ctx, w - 210, 10, 198, 28, 8)
      ctx.fillStyle = 'rgba(60,40,10,0.85)'
      ctx.fill()
      ctx.fillStyle = '#fbbf24'
      ctx.font = 'bold 11px Inter'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText('MANUAL DEMO — not CSP', w - 111, 24)
    }

    if (hover) {
      // tooltip drawn via title attribute on canvas parent
    }
  }

  const onPointer = (e: React.PointerEvent, down = false, up = false) => {
    const rect = canvasRef.current!.getBoundingClientRect()
    const pos = posAt(e.clientX - rect.left, e.clientY - rect.top)
    if (!down && !up) setHover(pos)
    if (!pos || !grid) return

    if (mode === 'edit' && down) {
      const isStation = pos[0] === grid.station[0] && pos[1] === grid.station[1]
      const isDirty = grid.dirty.some((d) => d.pos[0] === pos[0] && d.pos[1] === pos[1])
      if (isStation || isDirty) {
        onToast?.('Cannot edit station or dirty cells', 'warning')
        return
      }
      const has = obstacleSet.has(key(pos))
      const adding = e.button === 2 ? false : !has
      editPaintRef.current = adding
      applyEdit(pos, adding)
      return
    }
    if (mode === 'edit' && editPaintRef.current != null && e.buttons) {
      applyEdit(pos, editPaintRef.current)
      return
    }
    if (up) editPaintRef.current = null

    if (mode === 'search' && down) {
      const isObs = obstacleSet.has(key(pos))
      if (isObs) {
        onToast?.('Cannot place marker on an obstacle', 'error')
        return
      }
      if (e.button === 2 || e.shiftKey) onStartGoal?.(start ?? null, pos)
      else onStartGoal?.(pos, goal ?? null)
    }
  }

  function applyEdit(pos: Pos, add: boolean) {
    if (!grid || !onGridEdit) return
    const obstacles = add
      ? [...grid.obstacles, pos]
      : grid.obstacles.filter((p) => !(p[0] === pos[0] && p[1] === pos[1]))
    // dedupe
    const uniq = Array.from(new Set(obstacles.map(key))).map((k) => {
      const [r, c] = k.split(',').map(Number)
      return [r, c] as Pos
    })
    onGridEdit({ ...grid, obstacles: uniq })
    if (add) obstaclePopRef.current.set(key(pos), 0)
  }

  // Keyboard
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.code === 'Space') {
        e.preventDefault()
        setPlaying((p) => !p)
      } else if (e.code === 'ArrowRight') {
        setPlaying(false)
        advance(1)
      } else if (e.key.toLowerCase() === 'r') {
        api.reset()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  const tip =
    hover && grid
      ? `(${hover[0]}, ${hover[1]}) — ${
          obstacleSet.has(key(hover))
            ? 'obstacle'
            : hover[0] === grid.station[0] && hover[1] === grid.station[1]
              ? 'station'
              : grid.dirty.find((d) => d.pos[0] === hover[0] && d.pos[1] === hover[1])?.label ??
                'free'
        }`
      : undefined

  return (
    <div
      ref={wrapRef}
      className={`relative min-h-[320px] w-full flex-1 overflow-hidden rounded-[22px] ${className}`}
      title={tip}
    >
      <canvas
        ref={canvasRef}
        className="h-full w-full touch-none"
        onPointerMove={(e) => onPointer(e)}
        onPointerDown={(e) => {
          e.currentTarget.setPointerCapture(e.pointerId)
          onPointer(e, true)
        }}
        onPointerUp={(e) => onPointer(e, false, true)}
        onContextMenu={(e) => e.preventDefault()}
      />
    </div>
  )
})

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  const rr = Math.min(r, w / 2, h / 2)
  ctx.beginPath()
  ctx.moveTo(x + rr, y)
  ctx.arcTo(x + w, y, x + w, y + h, rr)
  ctx.arcTo(x + w, y + h, x, y + h, rr)
  ctx.arcTo(x, y + h, x, y, rr)
  ctx.arcTo(x, y, x + w, y, rr)
  ctx.closePath()
}

function hexAlpha(hex: string, a: number) {
  const c = hex.replace('#', '')
  const n = parseInt(c.length === 3 ? c.split('').map((x) => x + x).join('') : c, 16)
  const r = (n >> 16) & 255
  const g = (n >> 8) & 255
  const b = n & 255
  return `rgba(${r},${g},${b},${a})`
}
