import { useCallback, useRef, useState } from 'react'
import { Upload, AlertCircle } from 'lucide-react'

const MAX_SIZE_MB = 25
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024

interface UploadDropzoneProps {
  onUpload: (file: File) => Promise<void>
  disabled?: boolean
  isDark?: boolean
  compact?: boolean
}

export function UploadDropzone({ onUpload, disabled, isDark = false, compact = false }: UploadDropzoneProps) {
  const [dragging, setDragging] = useState(false)
  const [sizeError, setSizeError] = useState(false)
  const [uploading, setUploading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback(
    async (file: File) => {
      setSizeError(false)
      if (file.size > MAX_SIZE_BYTES) {
        setSizeError(true)
        return
      }
      if (file.type !== 'application/pdf' && !file.name.endsWith('.pdf')) {
        return
      }
      setUploading(true)
      try {
        await onUpload(file)
      } finally {
        setUploading(false)
      }
    },
    [onUpload],
  )

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      const file = e.dataTransfer.files[0]
      if (file) void handleFile(file)
    },
    [handleFile],
  )

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(true)
  }

  const onDragLeave = () => setDragging(false)

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) void handleFile(file)
    e.target.value = ''
  }

  return (
    <div>
      <div
        onClick={() => !disabled && !uploading && inputRef.current?.click()}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        className={`border-2 border-dashed rounded-xl text-center cursor-pointer transition-colors ${
          compact ? 'p-3' : 'p-6'
        } ${
          isDark
            ? dragging
              ? 'border-indigo-400 bg-indigo-900/40 text-white'
              : 'border-white/20 bg-white/5 hover:border-indigo-400 hover:bg-white/10 text-slate-300'
            : dragging
            ? 'border-indigo-500 bg-indigo-50/80 text-slate-800'
            : 'border-slate-300 bg-white hover:border-indigo-400 hover:bg-slate-50/50 text-slate-600'
        } ${disabled || uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="hidden"
          onChange={onInputChange}
          disabled={disabled || uploading}
        />
        {uploading ? (
          <div className="flex flex-col items-center gap-1.5 py-1">
            <span className="animate-spin h-5 w-5 border-2 border-indigo-500 border-t-transparent rounded-full" />
            <p className="text-xs font-medium text-indigo-400">Uploading PDF…</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1">
            <Upload size={compact ? 16 : 24} className={isDark ? 'text-indigo-400' : 'text-indigo-600'} />
            <p className={`${compact ? 'text-xs' : 'text-sm font-medium'} leading-tight`}>
              Drop PDF or <span className="text-indigo-400 font-semibold underline">browse</span>
            </p>
            {!compact && <p className="text-xs text-slate-400">Max {MAX_SIZE_MB} MB • PDF research papers</p>}
          </div>
        )}
      </div>
      {sizeError && (
        <div className="flex items-center gap-1.5 mt-2 text-red-400 text-xs font-medium">
          <AlertCircle size={12} />
          File exceeds {MAX_SIZE_MB} MB limit
        </div>
      )}
    </div>
  )
}
