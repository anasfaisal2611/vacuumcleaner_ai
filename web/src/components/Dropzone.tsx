import { Upload } from 'lucide-react'
import { useCallback, useState } from 'react'

export function Dropzone({
  accept = '.txt',
  onText,
  label = 'Drop a .txt file here, or click to browse',
}: {
  accept?: string
  onText: (text: string, filename: string) => void
  label?: string
}) {
  const [over, setOver] = useState(false)

  const read = useCallback(
    (file: File) => {
      const reader = new FileReader()
      reader.onload = () => onText(String(reader.result ?? ''), file.name)
      reader.readAsText(file)
    },
    [onText],
  )

  return (
    <label
      className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border border-dashed px-4 py-8 text-center transition ${
        over
          ? 'border-teal-400 bg-teal-400/10'
          : 'border-[var(--border)] bg-white/5 hover:bg-white/8'
      }`}
      onDragOver={(e) => {
        e.preventDefault()
        setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setOver(false)
        const file = e.dataTransfer.files?.[0]
        if (file) read(file)
      }}
    >
      <Upload className="text-teal-300" size={22} />
      <span className="text-sm text-[var(--text-muted)]">{label}</span>
      <input
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) read(file)
        }}
      />
    </label>
  )
}
