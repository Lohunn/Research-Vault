import { StatusBadge } from './StatusBadge'
import { Trash2, FileText } from 'lucide-react'
import type { Document } from '../api/types'

interface DocumentListProps {
  documents: Document[]
  onDelete: (docId: string) => void
}

export function DocumentList({ documents, onDelete }: DocumentListProps) {
  if (documents.length === 0) {
    return (
      <p className="text-sm text-slate-400 text-center py-4">
        No documents yet. Upload a PDF to get started.
      </p>
    )
  }

  return (
    <ul className="divide-y divide-slate-100">
      {documents.map((doc) => (
        <li key={doc.id} className="flex items-center gap-3 py-2.5 group">
          <FileText size={16} className="shrink-0 text-slate-400" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-800 truncate">
              {doc.title ?? doc.filename}
            </p>
            <div className="flex items-center gap-2 mt-0.5">
              <StatusBadge status={doc.status} />
              {doc.num_pages > 0 && (
                <span className="text-xs text-slate-400">{doc.num_pages} pages</span>
              )}
            </div>
          </div>
          <button
            onClick={() => onDelete(doc.id)}
            className="opacity-0 group-hover:opacity-100 p-1.5 rounded hover:bg-red-50
              text-slate-400 hover:text-red-500 transition-all"
            aria-label="Delete document"
          >
            <Trash2 size={14} />
          </button>
        </li>
      ))}
    </ul>
  )
}
