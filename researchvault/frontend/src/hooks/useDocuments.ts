import { useState, useEffect, useCallback, useRef } from 'react'
import { getDocuments, uploadDocument, deleteDocument } from '../api/client'
import type { Document } from '../api/types'

const POLL_INTERVAL = 2000

export function useDocuments(collectionId: string | null) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchDocuments = useCallback(async (id: string) => {
    try {
      const docs = await getDocuments(id)
      setDocuments(docs)
      return docs
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch documents')
      return []
    }
  }, [])

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  const startPolling = useCallback(
    (id: string) => {
      stopPolling()
      intervalRef.current = setInterval(async () => {
        const docs = await fetchDocuments(id)
        const anyProcessing = docs.some((d) => d.status === 'processing')
        if (!anyProcessing) stopPolling()
      }, POLL_INTERVAL)
    },
    [fetchDocuments, stopPolling],
  )

  useEffect(() => {
    if (!collectionId) {
      setDocuments([])
      stopPolling()
      return
    }
    setLoading(true)
    fetchDocuments(collectionId).then((docs) => {
      setLoading(false)
      const anyProcessing = docs.some((d) => d.status === 'processing')
      if (anyProcessing) startPolling(collectionId)
    })
    return () => stopPolling()
  }, [collectionId, fetchDocuments, startPolling, stopPolling])

  const upload = useCallback(
    async (file: File): Promise<Document> => {
      if (!collectionId) throw new Error('No collection selected')
      const doc = await uploadDocument(collectionId, file)
      setDocuments((prev) => [doc, ...prev])
      startPolling(collectionId)
      return doc
    },
    [collectionId, startPolling],
  )

  const remove = useCallback(async (docId: string) => {
    await deleteDocument(docId)
    setDocuments((prev) => prev.filter((d) => d.id !== docId))
  }, [])

  return { documents, loading, error, upload, remove, refetch: () => collectionId && fetchDocuments(collectionId) }
}
