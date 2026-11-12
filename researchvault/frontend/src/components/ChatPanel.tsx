import { useEffect, useRef, useState } from 'react'
import { Send } from 'lucide-react'
import { ChatMessage } from './ChatMessage'
import { CitationPanel } from './CitationPanel'
import type { Message, Citation } from '../api/types'

interface ChatPanelProps {
  messages: Message[]
  streaming: boolean
  onSend: (question: string) => void
}

export function ChatPanel({ messages, streaming, onSend }: ChatPanelProps) {
  const [input, setInput] = useState('')
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const q = input.trim()
    if (!q || streaming) return
    setInput('')
    onSend(q)
  }

  return (
    <div className="flex flex-col h-full relative">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto chat-scroll py-4 space-y-1">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <p className="text-slate-400 text-sm">Ask a question about your documents.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <ChatMessage
            key={i}
            message={msg}
            onCitationClick={(c) => setActiveCitation(c)}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-slate-200 p-4 bg-white">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about your documents…"
            disabled={streaming}
            className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 text-sm
              focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
              disabled:bg-slate-50 disabled:text-slate-400 transition-colors"
          />
          <button
            type="submit"
            disabled={streaming || !input.trim()}
            className="px-4 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium
              hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors flex items-center gap-2"
          >
            <Send size={16} />
            <span className="hidden sm:inline">Send</span>
          </button>
        </form>
      </div>

      {/* Citation panel */}
      <CitationPanel citation={activeCitation} onClose={() => setActiveCitation(null)} />
    </div>
  )
}
