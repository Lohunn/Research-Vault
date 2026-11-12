import type { Citation } from './types'

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

interface StreamCallbacks {
  onToken: (content: string) => void
  onCitations: (citations: Citation[]) => void
  onDone: () => void
  onError: (err: Error) => void
}

export async function streamChat(
  collectionId: string,
  question: string,
  history: { role: string; content: string }[],
  callbacks: StreamCallbacks,
): Promise<void> {
  let res: Response
  try {
    res = await fetch(`${BASE_URL}/collections/${collectionId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, history }),
    })
  } catch (err) {
    callbacks.onError(err instanceof Error ? err : new Error(String(err)))
    return
  }

  if (!res.ok) {
    let detail = ''
    try {
      const json = await res.json()
      detail = json.detail ?? JSON.stringify(json)
    } catch {
      detail = res.statusText
    }
    callbacks.onError(new Error(`${res.status}: ${detail}`))
    return
  }

  const reader = res.body?.getReader()
  if (!reader) {
    callbacks.onError(new Error('No readable stream'))
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed || !trimmed.startsWith('data:')) continue

        const dataStr = trimmed.slice(5).trim()
        if (!dataStr || dataStr === '[DONE]') continue

        try {
          const event = JSON.parse(dataStr) as {
            type: 'token' | 'citations' | 'done' | 'error'
            content?: string
            citations?: Citation[]
            error?: string
          }

          if (event.type === 'token' && event.content) {
            callbacks.onToken(event.content)
          } else if (event.type === 'citations' && event.citations) {
            callbacks.onCitations(event.citations)
          } else if (event.type === 'done') {
            callbacks.onDone()
          } else if (event.type === 'error') {
            callbacks.onError(new Error(event.error ?? 'Stream error'))
          }
        } catch {
          // Ignore malformed JSON events
        }
      }
    }
  } catch (err) {
    callbacks.onError(err instanceof Error ? err : new Error(String(err)))
  } finally {
    reader.releaseLock()
    callbacks.onDone()
  }
}
