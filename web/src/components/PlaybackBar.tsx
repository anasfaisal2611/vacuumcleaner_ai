import { Pause, Play, RotateCcw, SkipForward, StepForward } from 'lucide-react'
import { GradientButton } from './GradientButton'

export interface PlaybackApi {
  playing: boolean
  speed: number
  play: () => void
  pause: () => void
  step: () => void
  reset: () => void
  skip: () => void
  setSpeed: (s: number) => void
}

export function PlaybackBar({ api }: { api: PlaybackApi }) {
  return (
    <div className="glass flex flex-wrap items-center gap-2 !rounded-2xl p-3">
      <GradientButton
        type="button"
        onClick={() => (api.playing ? api.pause() : api.play())}
        aria-label={api.playing ? 'Pause' : 'Play'}
      >
        {api.playing ? <Pause size={16} /> : <Play size={16} />}
        {api.playing ? 'Pause' : 'Play'}
      </GradientButton>
      <GradientButton type="button" variant="ghost" onClick={api.step} aria-label="Step">
        <StepForward size={16} /> Step
      </GradientButton>
      <GradientButton type="button" variant="ghost" onClick={api.reset} aria-label="Reset">
        <RotateCcw size={16} /> Reset
      </GradientButton>
      <GradientButton type="button" variant="ghost" onClick={api.skip} aria-label="Skip">
        <SkipForward size={16} /> Skip
      </GradientButton>
      <label className="ml-auto flex items-center gap-2 text-xs text-[var(--text-muted)]">
        Speed
        <input
          type="range"
          min={0.25}
          max={8}
          step={0.25}
          value={api.speed}
          onChange={(e) => api.setSpeed(Number(e.target.value))}
          className="w-28 accent-teal-400"
          aria-label="Playback speed"
        />
        <span className="tabular w-10">{api.speed.toFixed(2)}x</span>
      </label>
    </div>
  )
}
