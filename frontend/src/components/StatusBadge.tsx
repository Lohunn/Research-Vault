interface StatusBadgeProps {
  status: 'processing' | 'ready' | 'failed'
}

export function StatusBadge({ status }: StatusBadgeProps) {
  if (status === 'processing') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
        <span className="animate-spin h-3 w-3 border-2 border-yellow-500 border-t-transparent rounded-full" />
        Processing
      </span>
    )
  }
  if (status === 'ready') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
        <span className="h-2 w-2 rounded-full bg-green-500" />
        Ready
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
      <span className="h-2 w-2 rounded-full bg-red-500" />
      Failed
    </span>
  )
}
