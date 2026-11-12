interface CitationBadgeProps {
  index: number
  onClick: (index: number) => void
}

export function CitationBadge({ index, onClick }: CitationBadgeProps) {
  return (
    <button
      onClick={() => onClick(index)}
      className="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1.5 rounded-full
        bg-indigo-600 text-white text-xs font-semibold leading-none
        hover:bg-indigo-700 transition-colors cursor-pointer align-middle"
      aria-label={`View citation ${index}`}
    >
      {index}
    </button>
  )
}
