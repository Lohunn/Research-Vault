import { useEffect } from 'react'
import { Sidebar } from '../components/Sidebar'
import { ChatPanel } from '../components/ChatPanel'
import { EmptyState } from '../components/EmptyState'
import { useCollections } from '../hooks/useCollections'
import { useDocuments } from '../hooks/useDocuments'
import { useChat } from '../hooks/useChat'
import type { Collection, Document } from '../api/types'

interface HomePageProps {
  selectedId: string | null
  onSelectCollection: (id: string) => void
  onToast: (message: string, type: 'error' | 'success') => void
}

export function HomePage({ selectedId, onSelectCollection, onToast }: HomePageProps) {
  const { collections, addCollection, error: colError } = useCollections()
  const { documents, upload, remove, error: docError } = useDocuments(selectedId)
  const { messages, streaming, sendMessage, error: chatError } = useChat(selectedId)

  // Auto-select the first collection on initial load so user is never stuck on an empty screen
  useEffect(() => {
    if (!selectedId && collections.length > 0) {
      onSelectCollection(collections[0].id)
    }
  }, [collections, selectedId, onSelectCollection])

  // Propagate errors to toast
  useEffect(() => { if (colError) onToast(colError, 'error') }, [colError, onToast])
  useEffect(() => { if (docError) onToast(docError, 'error') }, [docError, onToast])
  useEffect(() => { if (chatError) onToast(chatError, 'error') }, [chatError, onToast])

  const handleCreateCollection = async (name: string) => {
    try {
      const col = await addCollection(name)
      onSelectCollection(col.id)
      onToast(`Collection "${name}" created`, 'success')
    } catch (err) {
      onToast(err instanceof Error ? err.message : 'Failed to create collection', 'error')
    }
  }

  const handleUpload = async (file: File) => {
    try {
      await upload(file)
      onToast(`Uploaded "${file.name}" — processing…`, 'success')
    } catch (err) {
      onToast(err instanceof Error ? err.message : 'Upload failed', 'error')
    }
  }

  const handleDelete = async (docId: string) => {
    try {
      await remove(docId)
      onToast('Document deleted', 'success')
    } catch (err) {
      onToast(err instanceof Error ? err.message : 'Delete failed', 'error')
    }
  }

  // Active collection metadata
  const activeCollection = collections.find((c) => c.id === selectedId)

  // Build a map of collectionId → Document[] for the sidebar
  const documentsMap: Record<string, Document[]> = {}
  if (selectedId) documentsMap[selectedId] = documents

  const colsWithCount = collections.map((c: Collection) => ({
    ...c,
    docCount: c.id === selectedId ? documents.length : 0,
  }))

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
      <Sidebar
        collections={colsWithCount}
        documentsMap={documentsMap}
        selectedId={selectedId}
        onSelectCollection={onSelectCollection}
        onCreateCollection={handleCreateCollection}
        onUpload={handleUpload}
        onDeleteDocument={handleDelete}
      />

      {/* Main area */}
      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {selectedId == null ? (
          <EmptyState
            variant={collections.length === 0 ? 'no-collections' : 'no-selection'}
            onCreateCollection={handleCreateCollection}
            onSelectFirst={() => collections[0] && onSelectCollection(collections[0].id)}
          />
        ) : (
          <ChatPanel
            collectionName={activeCollection?.name ?? 'Collection'}
            documents={documents}
            messages={messages}
            streaming={streaming}
            onSend={sendMessage}
            onUpload={handleUpload}
            onDeleteDocument={handleDelete}
          />
        )}
      </main>
    </div>
  )
}
