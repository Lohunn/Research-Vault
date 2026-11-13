import { useState } from 'react'
import { BookOpen, MessageSquare, Plus, ArrowRight } from 'lucide-react'

type EmptyVariant = 'no-collections' | 'no-selection' | 'no-messages'

interface EmptyStateProps {
  variant: EmptyVariant
  onCreateCollection?: (name: string) => Promise<void>
  onSelectFirst?: () => void
}

export function EmptyState({ variant, onCreateCollection, onSelectFirst }: EmptyStateProps) {
  const [collectionName, setCollectionName] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const name = collectionName.trim()
    if (!name || !onCreateCollection || submitting) return
    setSubmitting(true)
    try {
      await onCreateCollection(name)
      setCollectionName('')
    } finally {
      setSubmitting(false)
    }
  }

  if (variant === 'no-collections') {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-8 max-w-md mx-auto">
        <div className="w-16 h-16 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shadow-sm">
          <BookOpen size={32} />
        </div>
        <div>
          <h2 className="text-xl font-bold text-slate-800">Welcome to ResearchVault</h2>
          <p className="text-sm text-slate-500 mt-1">
            Create your first collection to upload papers and get answers with exact page citations.
          </p>
        </div>

        {onCreateCollection && (
          <form onSubmit={handleSubmit} className="w-full flex gap-2 mt-2">
            <input
              type="text"
              value={collectionName}
              onChange={(e) => setCollectionName(e.target.value)}
              placeholder="e.g., NLP Papers, Thesis, BioMed…"
              className="flex-1 px-4 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white shadow-sm"
              disabled={submitting}
              autoFocus
            />
            <button
              type="submit"
              disabled={submitting || !collectionName.trim()}
              className="px-4 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5 shadow-sm shrink-0"
            >
              <Plus size={16} />
              <span>{submitting ? 'Creating…' : 'Create'}</span>
            </button>
          </form>
        )}
      </div>
    )
  }

  if (variant === 'no-selection') {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-8 max-w-sm mx-auto">
        <div className="w-16 h-16 rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-400">
          <MessageSquare size={32} />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-slate-700">Select a Collection</h2>
          <p className="text-sm text-slate-500 mt-1">
            Choose a collection from the sidebar to view documents and start chatting.
          </p>
        </div>
        {onSelectFirst && (
          <button
            onClick={onSelectFirst}
            className="mt-2 inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 transition-colors shadow-sm"
          >
            Open First Collection <ArrowRight size={16} />
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-center px-8">
      <MessageSquare size={36} className="text-slate-300" />
      <h2 className="text-lg font-semibold text-slate-700">Ask your first question</h2>
      <p className="text-sm text-slate-400 max-w-xs">
        Type a question below to query your uploaded documents with page-level citations.
      </p>
    </div>
  )
}
