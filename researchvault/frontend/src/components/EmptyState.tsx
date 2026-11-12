import { BookOpen, MessageSquare } from 'lucide-react'

type EmptyVariant = 'no-collections' | 'no-selection' | 'no-messages'

interface EmptyStateProps {
  variant: EmptyVariant
}

const configs: Record<EmptyVariant, { icon: React.ReactNode; title: string; description: string }> = {
  'no-collections': {
    icon: <BookOpen size={40} className="text-slate-300" />,
    title: 'No collections yet',
    description: 'Create a collection from the sidebar to get started.',
  },
  'no-selection': {
    icon: <MessageSquare size={40} className="text-slate-300" />,
    title: 'Select a collection',
    description: 'Choose a collection from the sidebar to start chatting.',
  },
  'no-messages': {
    icon: <MessageSquare size={40} className="text-slate-300" />,
    title: 'Ask your first question',
    description: 'Type a question below to query your documents.',
  },
}

export function EmptyState({ variant }: EmptyStateProps) {
  const { icon, title, description } = configs[variant]
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-center px-8">
      {icon}
      <h2 className="text-lg font-semibold text-slate-600">{title}</h2>
      <p className="text-sm text-slate-400 max-w-xs">{description}</p>
    </div>
  )
}
