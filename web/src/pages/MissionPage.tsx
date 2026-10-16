import { GripVertical } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { ApiRequestError, api } from '../api'
import { Dropzone } from '../components/Dropzone'
import { GlassCard } from '../components/GlassCard'
import { GradientButton } from '../components/GradientButton'
import { GridCanvas, type GridCanvasHandle } from '../components/GridCanvas'
import { PlaybackBar } from '../components/PlaybackBar'
import { useAppStore } from '../store'
import type { MissionResult } from '../types'

export function MissionPage() {
  const grid = useAppStore((s) => s.grid)
  const rawText = useAppStore((s) => s.rawText)
  const backend = useAppStore((s) => s.backend)
  const pushToast = useAppStore((s) => s.pushToast)

  const [schedule, setSchedule] = useState<string[]>([])
  const [assignment, setAssignment] = useState<Record<string, string> | null>(null)
  const [scheduleText, setScheduleText] = useState('')
  const [source, setSource] = useState<'csp' | 'manual'>('manual')
  const [algo, setAlgo] = useState('bfs')
  const [result, setResult] = useState<MissionResult | null>(null)
  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const canvasRef = useRef<GridCanvasHandle>(null)
  const [pb, setPb] = useState({ playing: false, speed: 1 })

  useEffect(() => {
    if (grid) setSchedule(grid.dirty.map((d) => d.label))
  }, [grid])

  useEffect(() => {
    const id = window.setInterval(() => {
      const c = canvasRef.current
      if (c) setPb({ playing: c.playing, speed: c.speed })
    }, 200)
    return () => clearInterval(id)
  }, [])

  const missing = !backend?.csp || !backend?.integration

  async function generateCsp() {
    if (!rawText || !scheduleText) {
      pushToast('Load environment and a Schedule.txt first', 'warning')
      return
    }
    try {
      const res = await api.generateSchedule({ envText: rawText, scheduleText })
      if (res.schedule) {
        setSchedule(res.schedule)
        setAssignment(res.assignment)
        setSource('csp')
        pushToast(res.message, 'success')
      } else {
        pushToast(res.message, 'error')
      }
    } catch (e) {
      pushToast(e instanceof ApiRequestError ? e.message : 'CSP unavailable', 'error')
      setSource('manual')
    }
  }

  async function startMission() {
    if (!rawText || !schedule.length) {
      pushToast('Need environment + schedule order', 'warning')
      return
    }
    try {
      const res = await api.executeMission({
        envText: rawText,
        schedule,
        algorithm: algo,
        scheduleSource: source,
      })
      setResult(res)
      const legs = res.legs.map((l) => l.path ?? []).filter((p) => p.length)
      canvasRef.current?.loadMission(res.completePath, legs, res.scheduleSource === 'manual')
      pushToast(res.message, res.success ? 'success' : 'error')
    } catch (e) {
      pushToast(e instanceof ApiRequestError ? e.message : 'Mission failed', 'error')
    }
  }

  function onDragStart(i: number) {
    setDragIndex(i)
  }
  function onDrop(i: number) {
    if (dragIndex == null || dragIndex === i) return
    const next = [...schedule]
    const [item] = next.splice(dragIndex, 1)
    next.splice(i, 0, item)
    setSchedule(next)
    setSource('manual')
    setDragIndex(null)
  }

  function downloadPng() {
    const canvas = document.querySelector('canvas')
    if (!canvas) return
    const url = canvas.toDataURL('image/png')
    const a = document.createElement('a')
    a.href = url
    a.download = 'mission-snapshot.png'
    a.click()
  }

  const canvasApi = canvasRef.current

  return (
    <div className="flex h-full flex-col gap-4 lg:flex-row">
      <div className="flex min-h-[420px] flex-1 flex-col gap-3">
        {missing ? (
          <div className="rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
            CSP/Integration not found yet (waiting for Member 2/3). Use the labeled{' '}
            <strong>Manual demo order</strong> below — it is <em>not</em> a CSP result.
          </div>
        ) : null}
        <GridCanvas ref={canvasRef} grid={grid} mode="mission" onToast={(m, k) => pushToast(m, k)} />
        {canvasApi ? (
          <PlaybackBar
            api={{
              playing: pb.playing,
              speed: pb.speed,
              play: () => canvasApi.play(),
              pause: () => canvasApi.pause(),
              step: () => canvasApi.step(),
              reset: () => canvasApi.reset(),
              skip: () => canvasApi.skip(),
              setSpeed: (s) => canvasApi.setSpeed(s),
            }}
          />
        ) : null}
        {result ? (
          <div className="h-2 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-teal-400 transition-all"
              style={{ width: result.success ? '100%' : '55%' }}
            />
          </div>
        ) : null}
      </div>

      <div className="flex w-full flex-col gap-4 lg:w-[340px]">
        <GlassCard title="Schedule">
          <Dropzone
            label="Drop Schedule.txt"
            onText={(text, name) => {
              setScheduleText(text)
              pushToast(`Loaded ${name}`, 'info')
            }}
          />
          <div className="mt-3 flex gap-2">
            <GradientButton type="button" variant="ghost" onClick={generateCsp}>
              Generate via CSP
            </GradientButton>
            <GradientButton
              type="button"
              variant="ghost"
              onClick={() => {
                setSource('manual')
                pushToast('Using MANUAL DEMO order', 'warning')
              }}
            >
              Manual demo
            </GradientButton>
          </div>
          <p className="mt-3 text-xs text-[var(--text-muted)]">
            Source:{' '}
            <span className={source === 'manual' ? 'text-amber-300' : 'text-teal-300'}>
              {source.toUpperCase()}
            </span>
            {source === 'manual' ? ' — not a CSP result' : ''}
          </p>
          <ul className="mt-3 space-y-2">
            {schedule.map((label, i) => (
              <li
                key={`${label}-${i}`}
                draggable
                onDragStart={() => onDragStart(i)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => onDrop(i)}
                className="flex cursor-grab items-center gap-2 rounded-xl bg-white/5 px-3 py-2 text-sm active:cursor-grabbing"
              >
                <GripVertical size={14} className="text-[var(--text-muted)]" />
                {assignment?.[label] ? (
                  <span className="rounded-md bg-violet-400/20 px-2 py-0.5 text-xs text-violet-200">
                    {assignment[label]}
                  </span>
                ) : null}
                <span className="font-semibold text-amber-300">{label}</span>
              </li>
            ))}
          </ul>
        </GlassCard>

        <GlassCard title="Execute">
          <select
            className="mb-3 w-full rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm"
            value={algo}
            onChange={(e) => setAlgo(e.target.value)}
          >
            <option value="bfs">BFS</option>
            <option value="astar">A*</option>
          </select>
          <GradientButton type="button" className="w-full" onClick={startMission}>
            Start mission
          </GradientButton>
          {result ? (
            <div className="mt-4 space-y-1 text-sm">
              <p
                className={`font-semibold ${result.success ? 'text-emerald-300' : 'text-rose-300'}`}
              >
                {result.success ? 'Mission complete' : 'Mission failed'}
              </p>
              <p className="text-[var(--text-muted)]">{result.message}</p>
              <p>
                Movements: <strong className="tabular">{result.totalMovements}</strong>
              </p>
              <p>
                Cost: <strong className="tabular">{result.totalCost}</strong>
              </p>
              <GradientButton type="button" variant="ghost" className="mt-2" onClick={downloadPng}>
                Download PNG
              </GradientButton>
            </div>
          ) : null}
        </GlassCard>
      </div>
    </div>
  )
}
