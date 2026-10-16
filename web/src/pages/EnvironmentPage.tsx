import { AlertTriangle } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { ApiRequestError, api } from '../api'
import { Dropzone } from '../components/Dropzone'
import { GlassCard } from '../components/GlassCard'
import { GradientButton } from '../components/GradientButton'
import { GridCanvas, type GridCanvasHandle } from '../components/GridCanvas'
import { PlaybackBar } from '../components/PlaybackBar'
import { StatCard } from '../components/StatCard'
import { ValidationList } from '../components/ValidationList'
import { useAppStore } from '../store'
import type { EnvironmentInfo } from '../types'

export function EnvironmentPage() {
  const applyEnvironment = useAppStore((s) => s.applyEnvironment)
  const pushToast = useAppStore((s) => s.pushToast)
  const grid = useAppStore((s) => s.grid)
  const validation = useAppStore((s) => s.validation)
  const unreachable = useAppStore((s) => s.unreachable)
  const updateGrid = useAppStore((s) => s.updateGrid)
  const [envs, setEnvs] = useState<EnvironmentInfo[]>([])
  const [edit, setEdit] = useState(false)
  const canvasRef = useRef<GridCanvasHandle>(null)
  const [playback, setPlayback] = useState({
    playing: false,
    speed: 1,
  })

  useEffect(() => {
    api.environments().then(setEnvs).catch(() => undefined)
  }, [])

  useEffect(() => {
    const id = window.setInterval(() => {
      const apiCanvas = canvasRef.current
      if (!apiCanvas) return
      setPlayback({ playing: apiCanvas.playing, speed: apiCanvas.speed })
    }, 200)
    return () => clearInterval(id)
  }, [])

  async function loadName(name: string) {
    try {
      const res = await api.loadEnvironment({ name })
      applyEnvironment(res, name)
      pushToast(`Loaded ${name}`, 'success')
    } catch (e) {
      const msg = e instanceof ApiRequestError ? e.message : 'Load failed'
      pushToast(msg, 'error')
    }
  }

  async function loadText(text: string, filename: string) {
    try {
      const res = await api.loadEnvironment({ text })
      applyEnvironment(res, filename)
      pushToast(`Loaded ${filename}`, 'success')
    } catch (e) {
      const msg = e instanceof ApiRequestError ? e.message : 'Load failed'
      pushToast(msg, 'error')
    }
  }

  async function download() {
    if (!grid) return
    try {
      const { text } = await api.saveEnvironment(grid)
      const blob = new Blob([text], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'Environment.txt'
      a.click()
      URL.revokeObjectURL(url)
      pushToast('Downloaded Environment.txt', 'success')
    } catch {
      pushToast('Save failed', 'error')
    }
  }

  const canvasApi = canvasRef.current

  return (
    <div className="flex h-full flex-col gap-4 lg:flex-row">
      <div className="flex min-h-[420px] flex-1 flex-col gap-3">
        <GridCanvas
          ref={canvasRef}
          grid={grid}
          mode={edit ? 'edit' : 'view'}
          onGridEdit={updateGrid}
          onToast={(m, k) => pushToast(m, k)}
        />
        {canvasApi ? (
          <PlaybackBar
            api={{
              playing: playback.playing,
              speed: playback.speed,
              play: () => canvasApi.play(),
              pause: () => canvasApi.pause(),
              step: () => canvasApi.step(),
              reset: () => canvasApi.reset(),
              skip: () => canvasApi.skip(),
              setSpeed: (s) => canvasApi.setSpeed(s),
            }}
          />
        ) : (
          <div className="glass h-14 !rounded-2xl" />
        )}
      </div>

      <div className="flex w-full flex-col gap-4 lg:w-[340px]">
        <GlassCard title="Load Environment">
          <div className="mb-3 flex flex-wrap gap-2">
            {envs.map((e) => (
              <GradientButton
                key={e.name}
                type="button"
                variant={e.label === 'Sample' ? 'primary' : 'ghost'}
                onClick={() => loadName(e.name)}
              >
                {e.label}
              </GradientButton>
            ))}
          </div>
          <Dropzone onText={loadText} />
          <div className="mt-3 flex gap-2">
            <GradientButton type="button" variant="ghost" onClick={() => setEdit((v) => !v)}>
              {edit ? 'Done editing' : 'Edit obstacles'}
            </GradientButton>
            <GradientButton type="button" variant="ghost" onClick={download} disabled={!grid}>
              Download .txt
            </GradientButton>
          </div>
        </GlassCard>

        {grid ? (
          <div className="grid grid-cols-2 gap-3">
            <StatCard label="Size" value={grid.rows} suffix={`×${grid.cols}`} />
            <StatCard label="Obstacles" value={grid.obstacles.length} accent="#94a3b8" />
            <StatCard label="Dirty" value={grid.dirty.length} accent="#f59e0b" />
            <StatCard
              label="Station"
              value={grid.station[0]}
              suffix={`,${grid.station[1]}`}
            />
          </div>
        ) : null}

        <GlassCard title="Validation">
          {validation.length ? (
            <ValidationList items={validation} />
          ) : (
            <p className="text-sm text-[var(--text-muted)]">Load a file to validate.</p>
          )}
        </GlassCard>

        {unreachable.length ? (
          <div className="flex gap-2 rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
            <AlertTriangle size={18} className="mt-0.5 shrink-0" />
            Unreachable dirty location(s): {unreachable.join(', ')}
          </div>
        ) : null}
      </div>
    </div>
  )
}
