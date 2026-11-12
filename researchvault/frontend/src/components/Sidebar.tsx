import { useState, useCallback } from 'react'
import { Plus, ChevronRight, BookMarked } from 'lucide-react'
import { CollectionItem } from './CollectionItem'
import { UploadDropzone } from './UploadDropzone'
import { DocumentList } from './DocumentList'
import type { Collection, Document } from '../api/types'

interface SidebarProps {
  collections: Collection[]
  documentsMap: Record<string, Document[]>
  selectedId: string | null
  onSelectCollection: (id: string) => void
  onCreateCollection: (name: string) => Promise<void>
  onUpload: (file: File) => Promise<void>
  onDeleteDocument: (docId: string) => void
}

export function Sidebar({
  collections,
  documentsMap,
  selectedId,
  onSelectCollection,
  onCreateCollection,
  onUpload,
  onDeleteDocument,
}: SidebarProps) {
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleCreate = useCallback(async () => {
    const name = newName.trim()
    if (!name) return
    setSubmitting(true)
    try {
      await onCreateCollection(name)
      setNewName('')
      setCreating(false)
    } finally {
      setSubmitting(false)
    }
  }, [newName, onCreateCollection])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') void handleCreate()
    if (e.key === 'Escape') {
      setCreating(false)
      setNewName('')
    }
  }

  return (
    <aside className="flex flex-col h-full bg-[#1e1e2e] text-white w-[280px] shrink-0">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-4 border-b border-white/10">
        <BookMarked size={20} className="text-indigo-400" />
        <span className="font-semibold text-lg tracking-tight">ResearchVault</span>
      </div>

      {/* Collections */}
      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
        <p className="text-xs uppercase tracking-wider text-slate-500 px-2 pb-1">Collections</p>

        {collections.length === 0 && (
          <p className="text-xs text-slate-500 px-2">No collections yet.</p>
        )}

        {collections.map((col) => {
          const docs = documentsMap[col.id] ?? []
          return (
            <CollectionItem
              key={col.id}
              collection={col}
              docCount={docs.length}
              isActive={col.id === selectedId}
              onSelect={() => onSelectCollection(col.id)}
            >
              <div className="space-y-2 pb-2">
                {selectedId === col.id && (
                  <>
                    <UploadDropzone onUpload={onUpload} />
                    <DocumentList documents={docs} onDelete={onDeleteDocument} />
                  </>
                )}
              </div>
            </CollectionItem>
          )
        })}

        {/* New collection input */}
        {creating && (
          <div className="px-2 py-1">
            <input
              autoFocus
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Collection name…"
              className="w-full bg-white/10 text-white placeholder-slate-400 text-sm px-3 py-1.5 rounded-lg
                focus:outline-none focus:ring-2 focus:ring-indigo-500 border border-white/20"
              disabled={submitting}
            />
            <div className="flex gap-1 mt-1.5">
              <button
                onClick={() => void handleCreate()}
                disabled={submitting || !newName.trim()}
                className="flex-1 text-xs bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50
                  text-white rounded px-2 py-1 transition-colors"
              >
                {submitting ? 'Creating…' : 'Create'}
              </button>
              <button
                onClick={() => { setCreating(false); setNewName('') }}
                className="flex-1 text-xs bg-white/10 hover:bg-white/20 text-slate-300 rounded px-2 py-1 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Footer: new collection button */}
      <div className="px-3 py-3 border-t border-white/10">
        <button
          onClick={() => setCreating(true)}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm
            text-slate-300 hover:bg-white/10 hover:text-white transition-colors"
        >
          <Plus size={16} />
          New Collection
        </button>
      </div>
    </aside>
  )
}
