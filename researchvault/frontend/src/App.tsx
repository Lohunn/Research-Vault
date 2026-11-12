import { useState, useCallback } from 'react'
import { HomePage } from './pages/HomePage'
import { ToastContainer } from './components/Toast'
import type { ToastData } from './api/types'

let toastCounter = 0

export default function App() {
  const [selectedCollectionId, setSelectedCollectionId] = useState<string | null>(null)
  const [toasts, setToasts] = useState<ToastData[]>([])

  const addToast = useCallback((message: string, type: 'error' | 'success') => {
    const id = String(++toastCounter)
    setToasts((prev) => [...prev, { id, message, type }])
  }, [])

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return (
    <>
      <HomePage
        selectedId={selectedCollectionId}
        onSelectCollection={setSelectedCollectionId}
        onToast={addToast}
      />
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </>
  )
}
