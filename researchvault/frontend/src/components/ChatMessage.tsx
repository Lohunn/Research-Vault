import ReactMarkdown from 'react-markdown'
import { CitationBadge } from './CitationBadge'
import type { Message, Citation } from '../api/types'

interface ChatMessageProps {
  message: Message
  onCitationClick: (citation: Citation) => void
}

/** Splits text on [n] patterns and returns an array of strings and citation indices */
function parseCitations(text: string): (string | number)[] {
  const parts: (string | number)[] = []
  const regex = /\[(\d+)\]/g
  let last = 0
  let match: RegExpExecArray | null
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index))
    parts.push(parseInt(match[1], 10))
    last = match.index + match[0].length
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts
}

export function ChatMessage({ message, onCitationClick }: ChatMessageProps) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end px-4 py-2">
        <div className="max-w-[75%] bg-indigo-100 text-slate-900 rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed">
          {message.content}
        </div>
      </div>
    )
  }

  // Assistant: render markdown but intercept [n] patterns with CitationBadge
  const citationMap = new Map(message.citations.map((c) => [c.index, c]))

  const renderContent = () => {
    // Split the content into parts using the citation regex and render each
    const parts = parseCitations(message.content)
    if (parts.every((p) => typeof p === 'string')) {
      // No citations found — render as pure markdown
      return (
        <ReactMarkdown className="prose prose-sm max-w-none prose-slate">
          {message.content}
        </ReactMarkdown>
      )
    }

    // Mix of text and citation badges
    return (
      <div className="prose prose-sm max-w-none prose-slate">
        {parts.map((part, i) => {
          if (typeof part === 'number') {
            const citation = citationMap.get(part)
            return citation ? (
              <CitationBadge key={i} index={part} onClick={() => onCitationClick(citation)} />
            ) : (
              <span key={i}>[{part}]</span>
            )
          }
          return (
            <ReactMarkdown key={i} className="inline">
              {part}
            </ReactMarkdown>
          )
        })}
      </div>
    )
  }

  return (
    <div className="flex justify-start px-4 py-2">
      <div className="max-w-[80%] bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm shadow-sm">
        {message.content === '' ? (
          <span className="inline-block w-2 h-4 bg-slate-400 animate-pulse rounded-sm" />
        ) : (
          renderContent()
        )}
      </div>
    </div>
  )
}
