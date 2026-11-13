import { StatusBadge } from './StatusBadge'
import { Trash2, FileText } from 'lucide-react'
import type { Document } from '../api/types'

interface DocumentListProps {
  documents: Document[]
  onDelete: (docId: string) => void
  isDark?: boolean
}

export function DocumentList({ documents, onDelete, isDark = false }: DocumentListProps) {
  if (documents.length === 0) {
    return (
      <p className={`text-xs text-center py-3 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
        No documents yet. Upload a PDF to get started.
      </p>
    )
  }

  return (
    <ul className={`divide-y ${isDark ? 'divide-white/10' : 'divide-slate-100'}`}>
      {documents.map((doc) => (
        <li key={doc.id} className="flex items-center gap-2.5 py-2 group">
          <FileText size={15} className={`shrink-0 ${isDark ? 'text-indigo-400' : 'text-indigo-600'}`} />
          <div className="flex-1 min-w-0">
            <p className={`text-xs font-medium truncate ${isDark ? 'text-slate-200' : 'text-slate-800'}`} title={doc.filename}>
              {doc.title ?? doc.filename}
            </p>
            <div className="flex items-center gap-2 mt-0.5">
              <StatusBadge status={doc.status} />
              {doc.num_pages > 0 && (
                <span className={`text-[10px] ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                  {doc.num_pages} {doc.num_pages === 1 ? 'page' : 'pages'}
                </span>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={() => onDelete(doc.id)}
            className={`opacity-0 group-hover:opacity-100 p-1 rounded transition-all ${
              isDark
                ? 'text-slate-400 hover:text-red-400 hover:bg-white/10'
                : 'text-slate-400 hover:text-red-500 hover:bg-red-50'
            }`}
            aria-label="Delete document"
            title="Delete document"
          >
            <Trash2 size={13} />
          </button>
        </li>
      ))}
    </ul>
  )
}
