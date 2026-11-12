export interface Collection {
  id: string
  name: string
  created_at: string
}

export interface Document {
  id: string
  collection_id: string
  filename: string
  title: string | null
  num_pages: number
  status: 'processing' | 'ready' | 'failed'
  uploaded_at: string
}

export interface Citation {
  index: number
  doc_id: string
  filename: string
  page: number
  snippet: string
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  citations: Citation[]
}

export interface ToastData {
  id: string
  message: string
  type: 'error' | 'success'
}
