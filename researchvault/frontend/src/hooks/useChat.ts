import { useState, useCallback, useEffect } from 'react'
import { streamChat } from '../api/stream'
import type { Message, Citation } from '../api/types'

export function useChat(collectionId: string | null) {
  const [messages, setMessages] = useState<Message[]>([])
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Clear messages and reset state when switching collections
  useEffect(() => {
    setMessages([])
    setStreaming(false)
    setError(null)
  }, [collectionId])

  const sendMessage = useCallback(
    async (question: string) => {
      if (!collectionId || streaming) return

      const userMessage: Message = { role: 'user', content: question, citations: [] }
      const assistantPlaceholder: Message = { role: 'assistant', content: '', citations: [] }

      // Append user message AND assistant empty placeholder
      setMessages((prev) => [...prev, userMessage, assistantPlaceholder])
      setStreaming(true)
      setError(null)

      const history = messages.map((m) => ({ role: m.role, content: m.content }))

      await streamChat(collectionId, question, history, {
        onToken(content) {
          setMessages((prev) => {
            if (prev.length === 0) return prev
            const lastIdx = prev.length - 1
            const last = prev[lastIdx]
            if (last.role !== 'assistant') return prev
            const updated = [...prev]
            updated[lastIdx] = { ...last, content: last.content + content }
            return updated
          })
        },
        onCitations(citations: Citation[]) {
          setMessages((prev) => {
            if (prev.length === 0) return prev
            const lastIdx = prev.length - 1
            const last = prev[lastIdx]
            if (last.role !== 'assistant') return prev
            const updated = [...prev]
            updated[lastIdx] = { ...last, citations }
            return updated
          })
        },
        onDone() {
          setStreaming(false)
        },
        onError(err: Error) {
          setError(err.message)
          setStreaming(false)
        },
      })
    },
    [collectionId, streaming, messages],
  )

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  return { messages, streaming, error, sendMessage, clearMessages }
}
