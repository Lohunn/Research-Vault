import type { Collection, Document } from './types'

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init)
  if (!res.ok) {
    let detail = ''
    try {
      const json = await res.json()
      detail = json.detail ?? JSON.stringify(json)
    } catch {
      detail = res.statusText
    }
    throw new Error(`${res.status}: ${detail}`)
  }
  return res.json() as Promise<T>
}

export async function getCollections(): Promise<Collection[]> {
  return request<Collection[]>('/collections')
}

export async function createCollection(name: string): Promise<Collection> {
  return request<Collection>('/collections', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
}

export async function getDocuments(collectionId: string): Promise<Document[]> {
  return request<Document[]>(`/collections/${collectionId}/documents`)
}

export async function uploadDocument(collectionId: string, file: File): Promise<Document> {
  const form = new FormData()
  form.append('file', file)
  return request<Document>(`/collections/${collectionId}/documents`, {
    method: 'POST',
    body: form,
  })
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/documents/${docId}`, { method: 'DELETE' })
  if (!res.ok) {
    throw new Error(`${res.status}: ${res.statusText}`)
  }
}
