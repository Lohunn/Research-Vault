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

  // Build a map of collectionId → Document[] for the sidebar
  const documentsMap: Record<string, Document[]> = {}
  if (selectedId) documentsMap[selectedId] = documents

  // Also get doc counts for all collections by using sidebar's context
  // (simple: only the selected collection's docs are loaded)
  const colsWithCount = collections.map((c: Collection) => ({
    ...c,
    docCount: c.id === selectedId ? documents.length : 0,
  }))

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
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
      <main className="flex-1 flex flex-col min-w-0">
        {selectedId == null ? (
          <EmptyState variant={collections.length === 0 ? 'no-collections' : 'no-selection'} />
        ) : (
          <ChatPanel
            messages={messages}
            streaming={streaming}
            onSend={sendMessage}
          />
        )}
      </main>
    </div>
  )
}
