import { useEffect, useRef, useState } from 'react'
import { Send, FileText, ChevronDown, ChevronUp, Upload, Sparkles } from 'lucide-react'
import { ChatMessage } from './ChatMessage'
import { CitationPanel } from './CitationPanel'
import { UploadDropzone } from './UploadDropzone'
import { DocumentList } from './DocumentList'
import type { Message, Citation, Document } from '../api/types'

interface ChatPanelProps {
  collectionName: string
  documents: Document[]
  messages: Message[]
  streaming: boolean
  onSend: (question: string) => void
  onUpload: (file: File) => Promise<void>
  onDeleteDocument: (docId: string) => void
}

export function ChatPanel({
  collectionName,
  documents,
  messages,
  streaming,
  onSend,
  onUpload,
  onDeleteDocument,
}: ChatPanelProps) {
  const [input, setInput] = useState('')
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null)
  const [showDocsPanel, setShowDocsPanel] = useState(false)
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

  const hasReadyDocs = documents.some((d) => d.status === 'ready')
  const isProcessingDocs = documents.some((d) => d.status === 'processing')

  return (
    <div className="flex flex-col h-full relative bg-slate-50">
      {/* Top Header Bar */}
      <header className="bg-white border-b border-slate-200 px-6 py-3.5 flex items-center justify-between shadow-sm z-10 shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shrink-0">
            <FileText size={18} />
          </div>
          <div className="min-w-0">
            <h1 className="font-semibold text-slate-800 text-sm md:text-base truncate">
              {collectionName}
            </h1>
            <p className="text-xs text-slate-500 flex items-center gap-1.5">
              <span>{documents.length} {documents.length === 1 ? 'paper' : 'papers'}</span>
              {isProcessingDocs && (
                <span className="inline-flex items-center gap-1 text-amber-600 font-medium">
                  • <span className="animate-spin h-2.5 w-2.5 border-2 border-amber-600 border-t-transparent rounded-full" />
                  Processing…
                </span>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowDocsPanel((v) => !v)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              showDocsPanel
                ? 'bg-indigo-50 border-indigo-300 text-indigo-700'
                : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
            }`}
          >
            <span>Papers ({documents.length})</span>
            {showDocsPanel ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </header>

      {/* Collapsible Documents Dropdown/Card */}
      {showDocsPanel && (
        <div className="bg-white border-b border-slate-200 px-6 py-4 shadow-md z-10 animate-fade-in max-h-96 overflow-y-auto">
          <div className="max-w-3xl mx-auto space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Uploaded Research Papers
              </h2>
              <span className="text-xs text-slate-400">PDFs are processed with page-level chunking</span>
            </div>

            <UploadDropzone onUpload={onUpload} />

            <div className="pt-2">
              <DocumentList documents={documents} onDelete={onDeleteDocument} />
            </div>
          </div>
        </div>
      )}

      {/* Main Chat / Upload Hero Area */}
      <div className="flex-1 overflow-y-auto chat-scroll py-6 px-4 md:px-8 space-y-4">
        {documents.length === 0 ? (
          /* Empty Documents Hero */
          <div className="max-w-xl mx-auto my-auto flex flex-col items-center justify-center text-center py-10">
            <div className="w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 mb-4 shadow-sm">
              <Upload size={28} />
            </div>
            <h2 className="text-lg font-bold text-slate-800 mb-1">
              Upload your research papers
            </h2>
            <p className="text-sm text-slate-500 mb-6 max-w-md">
              Drop one or more scientific papers (PDF) into this collection. We'll extract text, chunk by page, and generate embeddings for citation-grounded Q&A.
            </p>

            <div className="w-full bg-white rounded-2xl p-4 shadow-sm border border-slate-200">
              <UploadDropzone onUpload={onUpload} />
            </div>
          </div>
        ) : messages.length === 0 ? (
          /* Ready to Chat Welcome */
          <div className="max-w-lg mx-auto my-auto flex flex-col items-center justify-center text-center py-12">
            <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 mb-3">
              <Sparkles size={24} />
            </div>
            <h2 className="text-base font-semibold text-slate-800 mb-1">
              Ready to explore {collectionName}
            </h2>
            <p className="text-xs text-slate-500 mb-4 max-w-sm">
              Ask questions in plain English. Answers cite the exact paper, page number, and passage.
            </p>
            <div className="flex flex-wrap gap-2 justify-center max-w-md">
              {[
                'What is the primary contribution of this work?',
                'What methodology or dataset was evaluated?',
                'What are the key limitations discussed?',
              ].map((suggestion, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => onSend(suggestion)}
                  disabled={!hasReadyDocs}
                  className="text-xs bg-white border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/50 text-slate-700 px-3 py-1.5 rounded-full transition-colors disabled:opacity-50"
                >
                  "{suggestion}"
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Render messages */
          <div className="max-w-4xl mx-auto space-y-4">
            {messages.map((msg, i) => (
              <ChatMessage
                key={i}
                message={msg}
                onCitationClick={(c) => setActiveCitation(c)}
              />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input Bar */}
      <div className="border-t border-slate-200 p-4 bg-white shrink-0">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                documents.length === 0
                  ? 'Please upload a PDF first to ask questions…'
                  : 'Ask a question about your documents…'
              }
              disabled={streaming || documents.length === 0}
              className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 text-sm
                focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                disabled:bg-slate-50 disabled:text-slate-400 transition-colors bg-white shadow-sm"
            />
            <button
              type="submit"
              disabled={streaming || !input.trim() || documents.length === 0}
              className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium
                hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed
                transition-colors flex items-center gap-2 shadow-sm shrink-0"
            >
              <Send size={16} />
              <span className="hidden sm:inline">Ask</span>
            </button>
          </form>
        </div>
      </div>

      {/* Citation Slide-in Drawer */}
      <CitationPanel citation={activeCitation} onClose={() => setActiveCitation(null)} />
    </div>
  )
}
