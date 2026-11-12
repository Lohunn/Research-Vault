import { useCallback, useRef, useState } from 'react'
import { Upload, AlertCircle } from 'lucide-react'

const MAX_SIZE_MB = 25
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024

interface UploadDropzoneProps {
  onUpload: (file: File) => Promise<void>
  disabled?: boolean
}

export function UploadDropzone({ onUpload, disabled }: UploadDropzoneProps) {
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
        className={`border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-colors
          ${dragging ? 'border-indigo-500 bg-indigo-50' : 'border-slate-300 hover:border-indigo-400 hover:bg-slate-50'}
          ${disabled || uploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
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
          <div className="flex flex-col items-center gap-1">
            <span className="animate-spin h-6 w-6 border-2 border-indigo-500 border-t-transparent rounded-full" />
            <p className="text-xs text-slate-500">Uploading…</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1">
            <Upload size={20} className="text-slate-400" />
            <p className="text-xs text-slate-500">
              Drop PDF here or <span className="text-indigo-600 font-medium">browse</span>
            </p>
            <p className="text-xs text-slate-400">Max {MAX_SIZE_MB} MB</p>
          </div>
        )}
      </div>
      {sizeError && (
        <div className="flex items-center gap-1.5 mt-2 text-red-600 text-xs">
          <AlertCircle size={12} />
          File exceeds {MAX_SIZE_MB} MB limit
        </div>
      )}
    </div>
  )
}
