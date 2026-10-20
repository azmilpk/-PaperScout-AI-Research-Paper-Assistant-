import { useEffect, useRef, useState } from 'react'
import {
  getStatus,
  getPapers,
  loadSamplePaper,
  deletePaper,
  sendChat,
  uploadDocument,
} from './api/client'
import ChatMessage from './components/ChatMessage'
import CitationCard from './components/CitationCard'
import ApiKeyModal from './components/ApiKeyModal'
import './App.css'

const RESEARCH_QUESTIONS = [
  'Can you explain the main architecture used in this paper in simple terms?',
  'What is Scaled Dot-Product Attention and why divide by sqrt(d_k)?',
  'How does Multi-Head Attention work and what are the benefits?',
  'What are the benchmark BLEU scores on English-to-German translation?',
  'Why does self-attention have lower sequential operations than RNNs?',
]

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState(null)
  const [papers, setPapers] = useState([])
  const [selectedPaperId, setSelectedPaperId] = useState(null)
  const [activeCitations, setActiveCitations] = useState([])
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [isKeyModalOpen, setIsKeyModalOpen] = useState(false)
  const [currentView, setCurrentView] = useState('chat') // 'chat' | 'papers'
  const chatEndRef = useRef(null)
  const fileInputRef = useRef(null)

  const refreshAll = async () => {
    try {
      const [statusData, papersData] = await Promise.all([getStatus(), getPapers()])
      setStatus(statusData)
      setPapers(papersData.papers || [])
      setError('')

      // Auto-select first paper if none selected
      if (!selectedPaperId && papersData.papers && papersData.papers.length > 0) {
        setSelectedPaperId(papersData.papers[0].id)
      }
    } catch {
      setError('Backend is offline. Ensure FastAPI server is running on port 8000.')
      setStatus(null)
    }
  }

  useEffect(() => {
    refreshAll()
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const selectedPaper = papers.find((p) => p.id === selectedPaperId)

  const handleAsk = async (question) => {
    const query = question.trim()
    if (!query || loading) return

    if (status && !status.key_configured) {
      setError('Please configure your real LLM key (Hugging Face, Gemini, or OpenAI) to generate answers.')
      setIsKeyModalOpen(true)
      return
    }

    setError('')
    setLoading(true)
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: query }])

    try {
      const result = await sendChat(query, selectedPaperId)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: result.answer,
          citations: result.citations,
          model: result.llm_model,
          provider: result.llm_provider,
        },
      ])
      if (result.citations && result.citations.length > 0) {
        setActiveCitations(result.citations)
      }
      await refreshAll()
    } catch (err) {
      const errMsg = err.message || 'An error occurred'
      setError(errMsg)
      if (
        errMsg.toLowerCase().includes('api key') ||
        errMsg.toLowerCase().includes('key configured')
      ) {
        setIsKeyModalOpen(true)
      }
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${errMsg}`, error: true },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleLoadSample = async () => {
    setUploading(true)
    setError('')
    try {
      const res = await loadSamplePaper()
      await refreshAll()
      if (res.paper) {
        setSelectedPaperId(res.paper.id)
      }
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
      const res = await uploadDocument(file)
      await refreshAll()
      if (res.paper) {
        setSelectedPaperId(res.paper.id)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
      event.target.value = ''
    }
  }

  const handleDeletePaper = async (paperId, e) => {
    e.stopPropagation()
    if (!window.confirm('Remove this paper from your library?')) return

    try {
      await deletePaper(paperId)
      if (selectedPaperId === paperId) {
        setSelectedPaperId(null)
      }
      await refreshAll()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="app">
      {/* Sidebar matching PaperPilot layout */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
          </div>
          <div>
            <h1>PaperScout</h1>
            <p>Research Paper Assistant</p>
          </div>
        </div>

        <button
          type="button"
          className="btn new-chat-btn"
          onClick={() => {
            setMessages([])
            setActiveCitations([])
            setCurrentView('chat')
          }}
        >
          <span>+</span> New Chat
        </button>

        {/* Navigation items */}
        <nav className="nav-menu">
          <button
            type="button"
            className={`nav-item ${currentView === 'papers' ? 'active' : ''}`}
            onClick={() => setCurrentView('papers')}
          >
            <span className="nav-icon">📚</span>
            <span>My Papers</span>
            <span className="count-pill">{papers.length}</span>
          </button>
          <button
            type="button"
            className={`nav-item ${currentView === 'chat' ? 'active' : ''}`}
            onClick={() => setCurrentView('chat')}
          >
            <span className="nav-icon">💬</span>
            <span>Chat &amp; Q&amp;A</span>
          </button>
          <button
            type="button"
            className="nav-item disabled"
            title="Coming in Phase 4"
          >
            <span className="nav-icon">⚖️</span>
            <span>Compare</span>
            <span className="badge-upcoming">Phase 4</span>
          </button>
          <button
            type="button"
            className="nav-item disabled"
            title="Coming in Phase 3"
          >
            <span className="nav-icon">📑</span>
            <span>Summaries</span>
            <span className="badge-upcoming">Phase 3</span>
          </button>
          <button
            type="button"
            className="nav-item"
            onClick={() => setIsKeyModalOpen(true)}
          >
            <span className="nav-icon">⚙️</span>
            <span>Settings &amp; Keys</span>
          </button>
        </nav>

        {/* Papers Quick List in Sidebar */}
        <section className="panel">
          <h2>Active Library ({papers.length})</h2>
          <div className="paper-quick-list">
            <button
              type="button"
              className={`paper-chip ${selectedPaperId === null ? 'selected' : ''}`}
              onClick={() => setSelectedPaperId(null)}
            >
              <span className="chip-icon">🌐</span>
              <div className="chip-details">
                <span className="chip-title">All Papers (Combined)</span>
                <span className="chip-meta">Search entire library</span>
              </div>
            </button>

            {papers.map((p) => (
              <div
                key={p.id}
                className={`paper-chip ${selectedPaperId === p.id ? 'selected' : ''}`}
                onClick={() => {
                  setSelectedPaperId(p.id)
                  setCurrentView('chat')
                }}
              >
                <span className="chip-icon">📄</span>
                <div className="chip-details">
                  <span className="chip-title">{p.title}</span>
                  <span className="chip-meta">{p.total_pages} pages • {p.chunk_count} chunks</span>
                </div>
                <button
                  type="button"
                  className="chip-del-btn"
                  title="Remove paper"
                  onClick={(e) => handleDeletePaper(p.id, e)}
                >
                  &times;
                </button>
              </div>
            ))}
          </div>

          <div className="action-group">
            <button
              type="button"
              className="btn primary"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? 'Processing...' : 'Upload Research Paper (.pdf)'}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.md"
              hidden
              onChange={handleFileUpload}
            />
            {papers.length === 0 && (
              <button
                type="button"
                className="btn secondary"
                onClick={handleLoadSample}
                disabled={uploading}
              >
                Load 'Attention Is All You Need'
              </button>
            )}
          </div>
        </section>

        <footer className="sidebar-footer">
          <span>LangChain + ChromaDB</span>
          <span className="mono">PaperScout Phase 1</span>
        </footer>
      </aside>

      {/* Main Content Area */}
      <main className="main">
        {/* Top bar with Active Paper Pill */}
        <header className="topbar">
          <div className="active-paper-pill">
            <span className="pdf-tag">PDF</span>
            <div className="pill-text">
              <span className="pill-title">
                {selectedPaper ? selectedPaper.title : 'All Uploaded Research Papers'}
              </span>
              <span className="pill-meta">
                {selectedPaper
                  ? `(${selectedPaper.total_pages} pages, ${selectedPaper.chunk_count} passages)`
                  : `(${papers.length} papers in library)`}
              </span>
            </div>
          </div>

          <div className="topbar-actions">
            <button
              type="button"
              className={`key-badge-btn ${status?.key_configured ? 'configured' : 'missing'}`}
              onClick={() => setIsKeyModalOpen(true)}
            >
              <span className={`dot ${status?.key_configured ? 'online' : 'offline'}`} />
              {status?.key_configured
                ? `${status.llm_provider.toUpperCase()}: ${status.llm_model}`
                : 'Set Free LLM Key'}
            </button>
          </div>
        </header>

        {error && <div className="banner error">{error}</div>}

        {/* View: Papers Library Manager */}
        {currentView === 'papers' ? (
          <div className="papers-library-view">
            <div className="library-header">
              <div>
                <h2>My Research Papers Library</h2>
                <p>Manage indexed academic papers, inspect chunks, and parse new PDFs</p>
              </div>
              <button
                type="button"
                className="btn primary"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
              >
                + Upload New Paper
              </button>
            </div>

            {papers.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-badge">No Papers Uploaded</div>
                <h3>Your library is empty</h3>
                <p>Upload any arXiv / conference PDF paper or load our bundled foundational paper.</p>
                <button
                  type="button"
                  className="btn primary"
                  onClick={handleLoadSample}
                  disabled={uploading}
                >
                  Load 'Attention Is All You Need' Paper
                </button>
              </div>
            ) : (
              <div className="papers-grid">
                {papers.map((p) => (
                  <div key={p.id} className="paper-card">
                    <div className="paper-card-header">
                      <span className="pdf-card-badge">PDF • {p.total_pages} Pages</span>
                      <button
                        type="button"
                        className="btn-danger-icon"
                        onClick={(e) => handleDeletePaper(p.id, e)}
                        title="Delete paper"
                      >
                        🗑️
                      </button>
                    </div>
                    <h3>{p.title}</h3>
                    <p className="paper-card-abstract">{p.abstract}</p>
                    <div className="paper-card-footer">
                      <span>{p.chunk_count} vector chunks</span>
                      <button
                        type="button"
                        className="btn secondary"
                        onClick={() => {
                          setSelectedPaperId(p.id)
                          setCurrentView('chat')
                        }}
                      >
                        Ask Questions &rarr;
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          /* View: Chat & Q&A */
          <div className="workspace">
            <section className="chat-panel">
              <div className="messages">
                {messages.length === 0 && !loading && (
                  <div className="empty-state">
                    <div className="empty-state-badge">PaperScout Grounded RAG</div>
                    <h3>Deep Research Paper Assistant</h3>
                    <p>
                      Ask detailed technical questions about model architectures, proofs, formulas,
                      or experimental results. Answers are grounded in the paper with exact citations.
                    </p>

                    <div className="suggested-questions">
                      <h4>Suggested Questions:</h4>
                      <div className="sample-list">
                        {RESEARCH_QUESTIONS.map((q) => (
                          <button
                            key={q}
                            type="button"
                            className="sample-chip"
                            onClick={() => handleAsk(q)}
                            disabled={loading}
                          >
                            {q}
                          </button>
                        ))}
                      </div>
                    </div>
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
                      Searching paper passages &amp; formulating verified answer...
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
                  placeholder={`Ask a question about ${selectedPaper ? selectedPaper.title : 'your research papers'}...`}
                  disabled={loading}
                />
                <button
                  type="submit"
                  className="btn primary"
                  disabled={loading || !input.trim()}
                >
                  Ask PaperScout
                </button>
              </form>
            </section>

            <aside className="citations-panel">
              <div className="citations-header">
                <h2>Source Citations</h2>
                <p>Passages and exact pages retrieved to answer your query</p>
              </div>

              {activeCitations.length === 0 ? (
                <div className="citations-empty">
                  In-text citations and verified passages will appear here after asking a question.
                </div>
              ) : (
                <div className="citations-list">
                  {activeCitations.map((citation, index) => (
                    <CitationCard
                      key={`${citation.section}-${index}`}
                      citation={citation}
                    />
                  ))}
                </div>
              )}
            </aside>
          </div>
        )}
      </main>

      <ApiKeyModal
        isOpen={isKeyModalOpen}
        onClose={() => setIsKeyModalOpen(false)}
        onKeySaved={refreshAll}
      />
    </div>
  )
}

export default App
