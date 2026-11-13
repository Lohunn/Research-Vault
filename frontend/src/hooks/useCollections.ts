import { useState, useEffect, useCallback } from 'react'
import { getCollections, createCollection } from '../api/client'
import type { Collection } from '../api/types'

export function useCollections() {
  const [collections, setCollections] = useState<Collection[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchCollections = useCallback(async () => {
    try {
      const data = await getCollections()
      setCollections(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch collections')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchCollections()
  }, [fetchCollections])

  const addCollection = useCallback(async (name: string): Promise<Collection> => {
    const col = await createCollection(name)
    setCollections((prev) => [...prev, col])
    return col
  }, [])

  return { collections, loading, error, refetch: fetchCollections, addCollection }
}
