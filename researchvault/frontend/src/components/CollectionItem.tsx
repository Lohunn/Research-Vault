import { useState, useEffect } from 'react'
import { ChevronRight, Files } from 'lucide-react'
import type { Collection } from '../api/types'

interface CollectionItemProps {
  collection: Collection
  docCount: number
  isActive: boolean
  onSelect: () => void
  children?: React.ReactNode
}

export function CollectionItem({
  collection,
  docCount,
  isActive,
  onSelect,
  children,
}: CollectionItemProps) {
  const [expanded, setExpanded] = useState(isActive)

  // Auto-expand when this collection becomes active so items are never hidden/stuck inside
  useEffect(() => {
    if (isActive) {
      setExpanded(true)
    }
  }, [isActive])

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation()
    setExpanded((v) => !v)
  }

  return (
    <div className="rounded-lg overflow-hidden">
      <div
        onClick={onSelect}
        className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm cursor-pointer select-none transition-colors
          ${isActive
            ? 'bg-indigo-600 text-white font-medium shadow-sm'
            : 'text-slate-300 hover:bg-white/10 hover:text-white'
          }`}
      >
        <button
          type="button"
          onClick={handleToggle}
          className={`p-0.5 rounded hover:bg-white/20 transition-transform ${expanded ? 'rotate-90' : ''}`}
          aria-label={expanded ? 'Collapse collection' : 'Expand collection'}
        >
          <ChevronRight size={14} />
        </button>
        <Files size={15} className="shrink-0" />
        <span className="flex-1 text-left truncate">{collection.name}</span>
        <span
          className={`text-xs px-1.5 py-0.5 rounded-full font-medium transition-colors
            ${isActive ? 'bg-white/20 text-white' : 'bg-slate-700 text-slate-300'}`}
        >
          {docCount}
        </span>
      </div>
      {expanded && children && (
        <div className="pl-3 pr-1 pt-2 pb-1 space-y-2 border-l-2 border-indigo-500/40 ml-4 mt-1">
          {children}
        </div>
      )}
    </div>
  )
}
