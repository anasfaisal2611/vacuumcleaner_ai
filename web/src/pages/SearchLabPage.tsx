import { useEffect, useRef, useState } from 'react'
import { ApiRequestError, api } from '../api'
import { GlassCard } from '../components/GlassCard'
import { GradientButton } from '../components/GradientButton'
import { GridCanvas, type GridCanvasHandle } from '../components/GridCanvas'
import { PlaybackBar } from '../components/PlaybackBar'
import { StatCard } from '../components/StatCard'
import { useAppStore } from '../store'
import type { Pos } from '../types'

export function SearchLabPage() {
  const grid = useAppStore((s) => s.grid)
  const rawText = useAppStore((s) => s.rawText)
  const pushToast = useAppStore((s) => s.pushToast)
  const setSearchResults = useAppStore((s) => s.setSearchResults)
  const searchResult = useAppStore((s) => s.searchResult)
  const searchResultB = useAppStore((s) => s.searchResultB)

  const [algo, setAlgo] = useState('bfs')
  const [start, setStart] = useState<Pos | null>(null)
  const [goal, setGoal] = useState<Pos | null>(null)
  const [sideBySide, setSideBySide] = useState(false)
  const [loading, setLoading] = useState(false)
  const [shake, setShake] = useState(false)
  const aRef = useRef<GridCanvasHandle>(null)
  const bRef = useRef<GridCanvasHandle>(null)
  const [pb, setPb] = useState({ playing: false, speed: 1 })

  useEffect(() => {
    if (grid) {
      setStart(grid.station)
      setGoal(grid.dirty[grid.dirty.length - 1]?.pos ?? null)
    }
  }, [grid])

  useEffect(() => {
    const id = window.setInterval(() => {
      const apiCanvas = aRef.current
      if (apiCanvas) setPb({ playing: apiCanvas.playing, speed: apiCanvas.speed })
    }, 200)
    return () => clearInterval(id)
  }, [])

  const labels = grid
    ? [
        { label: 'Station', pos: grid.station },
        ...grid.dirty.map((d) => ({ label: d.label, pos: d.pos })),
      ]
    : []

  async function run() {
    if (!grid || !rawText || !start || !goal) {
      pushToast('Load an environment and set start/goal', 'warning')
      return
    }
    setLoading(true)
    try {
      if (sideBySide) {
        const [bfs, astar] = await Promise.all([
          api.search({ envText: rawText, start, goal, algorithm: 'bfs' }),
          api.search({ envText: rawText, start, goal, algorithm: 'astar' }),
        ])
        setSearchResults(bfs, astar)
        aRef.current?.loadSearch(bfs, '#38bdf8')
        bRef.current?.loadSearch(astar, '#e879f9')
        if (!bfs.found) {
          setShake(true)
          setTimeout(() => setShake(false), 500)
          pushToast(bfs.message || 'No path found', 'error')
        } else {
          pushToast('Side-by-side search complete', 'success')
        }
      } else {
        const result = await api.search({
          envText: rawText,
          start,
          goal,
          algorithm: algo,
        })
        setSearchResults(result, null)
        aRef.current?.loadSearch(
          result,
          result.algorithm === 'astar' ? '#e879f9' : '#38bdf8',
        )
        if (!result.found) {
          setShake(true)
          setTimeout(() => setShake(false), 500)
          pushToast(result.message || 'No path found', 'error')
        } else pushToast('Search complete', 'success')
      }
    } catch (e) {
      pushToast(e instanceof ApiRequestError ? e.message : 'Search failed', 'error')
    } finally {
      setLoading(false)
    }
  }

  const canvasApi = aRef.current

  return (
    <div className="flex h-full flex-col gap-4 lg:flex-row">
      <div className="flex min-h-[420px] flex-1 flex-col gap-3">
        <div className={`flex flex-1 gap-3 ${sideBySide ? '' : ''}`}>
          <GridCanvas
            ref={aRef}
            grid={grid}
            mode="search"
            start={start}
            goal={goal}
            onStartGoal={(s, g) => {
              setStart(s)
              setGoal(g)
            }}
            onToast={(m, k) => pushToast(m, k)}
            className={sideBySide ? 'flex-1' : ''}
          />
          {sideBySide ? (
            <GridCanvas
              ref={bRef}
              grid={grid}
              mode="search"
              start={start}
              goal={goal}
              onStartGoal={(s, g) => {
                setStart(s)
                setGoal(g)
              }}
              onToast={(m, k) => pushToast(m, k)}
              className="flex-1"
            />
          ) : null}
        </div>
        {canvasApi ? (
          <PlaybackBar
            api={{
              playing: pb.playing,
              speed: pb.speed,
              play: () => {
                aRef.current?.play()
                bRef.current?.play()
              },
              pause: () => {
                aRef.current?.pause()
                bRef.current?.pause()
              },
              step: () => {
                aRef.current?.step()
                bRef.current?.step()
              },
              reset: () => {
                aRef.current?.reset()
                bRef.current?.reset()
              },
              skip: () => {
                aRef.current?.skip()
                bRef.current?.skip()
              },
              setSpeed: (s) => {
                aRef.current?.setSpeed(s)
                bRef.current?.setSpeed(s)
              },
            }}
          />
        ) : null}
      </div>

      <div className="flex w-full flex-col gap-4 lg:w-[340px]">
        <GlassCard title="Search Lab">
          <div className="mb-3 flex flex-wrap gap-1 rounded-xl bg-white/5 p-1">
            {['bfs', 'astar', 'ucs', 'greedy'].map((a) => (
              <button
                key={a}
                type="button"
                disabled={sideBySide}
                onClick={() => setAlgo(a)}
                className={`flex-1 rounded-lg px-2 py-1.5 text-xs font-semibold uppercase ${
                  algo === a && !sideBySide
                    ? 'bg-teal-400/20 text-teal-300'
                    : 'text-[var(--text-muted)]'
                }`}
              >
                {a}
              </button>
            ))}
          </div>
          <label className="mb-2 block text-xs text-[var(--text-muted)]">Start</label>
          <select
            className="mb-3 w-full rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm"
            value={start ? `${start[0]},${start[1]}` : ''}
            onChange={(e) => {
              const [r, c] = e.target.value.split(',').map(Number)
              setStart([r, c])
            }}
          >
            {labels.map((l) => (
              <option key={l.label} value={`${l.pos[0]},${l.pos[1]}`}>
                {l.label} ({l.pos[0]},{l.pos[1]})
              </option>
            ))}
          </select>
          <label className="mb-2 block text-xs text-[var(--text-muted)]">Goal</label>
          <select
            className="mb-3 w-full rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm"
            value={goal ? `${goal[0]},${goal[1]}` : ''}
            onChange={(e) => {
              const [r, c] = e.target.value.split(',').map(Number)
              setGoal([r, c])
            }}
          >
            {labels.map((l) => (
              <option key={l.label} value={`${l.pos[0]},${l.pos[1]}`}>
                {l.label} ({l.pos[0]},{l.pos[1]})
              </option>
            ))}
          </select>
          <label className="mb-3 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={sideBySide}
              onChange={(e) => setSideBySide(e.target.checked)}
            />
            Compare side by side (BFS | A*)
          </label>
          <GradientButton type="button" className="w-full" onClick={run} disabled={loading}>
            {loading ? 'Running…' : 'Run'}
          </GradientButton>
          <p className="mt-2 text-[11px] text-[var(--text-muted)]">
            Left-click = start · Right-click / Shift+click = goal
          </p>
        </GlassCard>

        <div
          className={`grid grid-cols-2 gap-3 transition ${shake ? 'animate-[shake_0.4s_ease]' : ''}`}
        >
          <StatCard label="Cost" value={searchResult?.cost ?? null} />
          <StatCard
            label="Expanded"
            value={searchResult?.nodesExpanded ?? null}
            accent={searchResult?.algorithm === 'astar' ? '#e879f9' : '#38bdf8'}
          />
          <StatCard label="Max frontier" value={searchResult?.frontierMaxSize ?? null} />
          <StatCard
            label="Runtime"
            value={searchResult?.runtimeMs ?? null}
            decimals={2}
            suffix=" ms"
          />
        </div>

        {searchResult && !searchResult.found ? (
          <GlassCard className="border-rose-400/40">
            <p className="font-semibold text-rose-300">No path found</p>
            <p className="mt-1 text-sm text-[var(--text-muted)]">{searchResult.message}</p>
          </GlassCard>
        ) : null}

        {sideBySide && searchResult && searchResultB && searchResult.found && searchResultB.found ? (
          <div className="rounded-2xl border border-teal-400/20 bg-teal-400/10 px-3 py-2 text-sm">
            {searchResultB.nodesExpanded < searchResult.nodesExpanded
              ? `A* expanded fewer nodes (${searchResultB.nodesExpanded} vs ${searchResult.nodesExpanded})`
              : searchResultB.nodesExpanded === searchResult.nodesExpanded
                ? 'Tie: same node expansions'
                : `BFS expanded fewer here (${searchResult.nodesExpanded} vs ${searchResultB.nodesExpanded})`}
          </div>
        ) : null}

        <GlassCard title="Path">
          <pre className="max-h-40 overflow-auto text-xs text-[var(--text-muted)]">
            {(searchResult?.path ?? []).map((p) => `(${p[0]},${p[1]})`).join(' → ') || '—'}
          </pre>
        </GlassCard>
      </div>
    </div>
  )
}
