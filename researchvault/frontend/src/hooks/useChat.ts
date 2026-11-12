import { useState, useCallback } from 'react'
import { streamChat } from '../api/stream'
import type { Message, Citation } from '../api/types'

export function useChat(collectionId: string | null) {
  const [messages, setMessages] = useState<Message[]>([])
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sendMessage = useCallback(
    async (question: string) => {
      if (!collectionId || streaming) return

      const userMessage: Message = { role: 'user', content: question, citations: [] }
      setMessages((prev) => [...prev, userMessage])
      setStreaming(true)
      setError(null)

      // Append empty assistant message that we'll fill as tokens arrive
      const assistantIndex = messages.length + 1
      setMessages((prev) => [...prev, { role: 'assistant', content: '', citations: [] }])

      const history = messages.map((m) => ({ role: m.role, content: m.content }))

      await streamChat(collectionId, question, history, {
        onToken(content) {
          setMessages((prev) => {
            const updated = [...prev]
            const msg = updated[assistantIndex]
            if (msg) {
              updated[assistantIndex] = { ...msg, content: msg.content + content }
            }
            return updated
          })
        },
        onCitations(citations: Citation[]) {
          setMessages((prev) => {
            const updated = [...prev]
            const msg = updated[assistantIndex]
            if (msg) {
              updated[assistantIndex] = { ...msg, citations }
            }
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
