import { useState } from 'react'
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
  const [expanded, setExpanded] = useState(false)

  const toggle = (e: React.MouseEvent) => {
    e.stopPropagation()
    setExpanded((v) => !v)
  }

  return (
    <div>
      <button
        onClick={onSelect}
        className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors
          ${isActive
            ? 'bg-indigo-600 text-white'
            : 'text-slate-300 hover:bg-white/10 hover:text-white'
          }`}
      >
        <button
          onClick={toggle}
          className={`p-0.5 rounded transition-transform ${expanded ? 'rotate-90' : ''}`}
        >
          <ChevronRight size={14} />
        </button>
        <Files size={15} className="shrink-0" />
        <span className="flex-1 text-left truncate">{collection.name}</span>
        <span
          className={`text-xs px-1.5 py-0.5 rounded-full font-medium
            ${isActive ? 'bg-white/20 text-white' : 'bg-slate-700 text-slate-300'}`}
        >
          {docCount}
        </span>
      </button>
      {expanded && children && (
        <div className="ml-4 mt-1">{children}</div>
      )}
    </div>
  )
}
