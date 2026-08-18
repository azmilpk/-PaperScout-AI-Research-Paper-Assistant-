import { useEffect, useRef, useState } from 'react'
import { getStatus, indexSample, sendChat, uploadDocument } from './api/client'
import ChatMessage from './components/ChatMessage'
import CitationCard from './components/CitationCard'
import './App.css'

const SAMPLE_QUESTIONS = [
  'What happens to my laptop if I resign?',
  'Can I use ChatGPT with company code?',
  'How many PTO days can I carry over?',
  'What is the home office setup allowance?',
]

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState(null)
  const [activeCitations, setActiveCitations] = useState([])
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const chatEndRef = useRef(null)
  const fileInputRef = useRef(null)

  const refreshStatus = async () => {
    try {
      const data = await getStatus()
      setStatus(data)
      setError('')
    } catch {
      setError('Backend is offline. Start the API server on port 8000.')
      setStatus(null)
    }
  }

  useEffect(() => {
    refreshStatus()
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleAsk = async (question) => {
    const query = question.trim()
    if (!query || loading) return

    setError('')
    setLoading(true)
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: query }])

    try {
      const result = await sendChat(query)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: result.answer, citations: result.citations },
      ])
      setActiveCitations(result.citations)
      await refreshStatus()
    } catch (err) {
      setError(err.message)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${err.message}`, error: true },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleIndexSample = async () => {
    setUploading(true)
    setError('')
    try {
      await indexSample()
      await refreshStatus()
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError('')
    try {
      await uploadDocument(file)
      await refreshStatus()
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
      event.target.value = ''
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">DM</div>
          <div>
            <h1>DocuMind AI</h1>
            <p>Grounded RAG Workspace</p>
          </div>
        </div>

        <section className="panel">
          <h2>Knowledge Base</h2>
          <div className={`status-badge ${status?.indexed ? 'ready' : 'empty'}`}>
            {status?.indexed
              ? `${status.chunk_count} chunks indexed`
              : 'No documents indexed'}
          </div>

          <div className="action-group">
            <button
              type="button"
              className="btn secondary"
              onClick={handleIndexSample}
              disabled={uploading}
            >
              Index Sample Policy
            </button>
            <button
              type="button"
              className="btn secondary"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              Upload .txt Document
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt"
              hidden
              onChange={handleFileUpload}
            />
          </div>
        </section>

        <section className="panel">
          <h2>Try asking</h2>
          <div className="sample-list">
            {SAMPLE_QUESTIONS.map((question) => (
              <button
                key={question}
                type="button"
                className="sample-chip"
                onClick={() => handleAsk(question)}
                disabled={loading}
              >
                {question}
              </button>
            ))}
          </div>
        </section>

        <footer className="sidebar-footer">
          <span>ChromaDB + Gemini RAG</span>
          <span className="mono">Step 3 Pipeline</span>
        </footer>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h2>Policy Q&amp;A Chat</h2>
            <p>Answers grounded in your indexed documents with source citations</p>
          </div>
          <div className="topbar-meta">
            <span className={`dot ${status?.indexed ? 'online' : 'offline'}`} />
            {status?.indexed ? 'Vector store ready' : 'Index a document to start'}
          </div>
        </header>

        {error && <div className="banner error">{error}</div>}

        <div className="workspace">
          <section className="chat-panel">
            <div className="messages">
              {messages.length === 0 && !loading && (
                <div className="empty-state">
                  <h3>Ask anything about your policy documents</h3>
                  <p>
                    DocuMind retrieves relevant passages from ChromaDB, then generates
                    a cited answer using the RAG pipeline from your learning scripts.
                  </p>
                </div>
              )}

              {messages.map((message, index) => (
                <ChatMessage
                  key={`${message.role}-${index}`}
                  message={message}
                  onShowCitations={setActiveCitations}
                />
              ))}

              {loading && (
                <div className="message assistant loading">
                  <div className="avatar">AI</div>
                  <div className="bubble">
                    <span className="typing">
                      <span />
                      <span />
                      <span />
                    </span>
                    Retrieving context and generating answer...
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <form
              className="composer"
              onSubmit={(event) => {
                event.preventDefault()
                handleAsk(input)
              }}
            >
              <input
                type="text"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Ask about remote work, PTO, AI policy..."
                disabled={loading}
              />
              <button type="submit" className="btn primary" disabled={loading || !input.trim()}>
                Send
              </button>
            </form>
          </section>

          <aside className="citations-panel">
            <div className="citations-header">
              <h2>Source Citations</h2>
              <p>Retrieved passages used to ground the answer</p>
            </div>

            {activeCitations.length === 0 ? (
              <div className="citations-empty">
                Citations from the latest answer will appear here.
              </div>
            ) : (
              <div className="citations-list">
                {activeCitations.map((citation, index) => (
                  <CitationCard key={`${citation.section}-${index}`} citation={citation} />
                ))}
              </div>
            )}
          </aside>
        </div>
      </main>
    </div>
  )
}

export default App
