import { X, FileText } from 'lucide-react'
import type { Citation } from '../api/types'

interface CitationPanelProps {
  citation: Citation | null
  onClose: () => void
}

export function CitationPanel({ citation, onClose }: CitationPanelProps) {
  if (!citation) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-30 md:hidden"
        onClick={onClose}
      />

      {/* Panel */}
      <div
        className="fixed bottom-0 right-0 md:top-0 w-full md:w-96 h-[60vh] md:h-full
          bg-white border-l border-t md:border-t-0 border-slate-200 shadow-xl z-40
          flex flex-col animate-slide-in"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-slate-50">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-indigo-600 text-white text-xs font-bold">
              {citation.index}
            </span>
            <span className="text-sm font-medium text-slate-700">Citation</span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded hover:bg-slate-200 transition-colors"
            aria-label="Close citation panel"
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div className="flex items-start gap-2">
            <FileText size={16} className="mt-0.5 shrink-0 text-slate-400" />
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-wide font-medium">Source</p>
              <p className="text-sm font-medium text-slate-800 break-all">{citation.filename}</p>
            </div>
          </div>

          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wide font-medium mb-1">Page</p>
            <p className="text-sm text-slate-800">{citation.page}</p>
          </div>

          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wide font-medium mb-2">Excerpt</p>
            <blockquote className="text-sm text-slate-700 leading-relaxed bg-slate-50 border-l-4 border-indigo-300 p-3 rounded-r-md italic">
              {citation.snippet}
            </blockquote>
          </div>
        </div>
      </div>
    </>
  )
}
