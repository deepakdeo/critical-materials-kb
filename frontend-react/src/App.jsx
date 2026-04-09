import { useState, useEffect, useRef, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import ChatInput from './components/ChatInput'
import MessageBubble from './components/MessageBubble'
import LoadingIndicator from './components/LoadingIndicator'
import WelcomeScreen from './components/WelcomeScreen'
import SourcesLibrary from './components/SourcesLibrary'
import { useQuery } from './hooks/useQuery'
import { useTheme } from './hooks/useTheme'

const STORAGE_KEY = 'cmkb-chat-messages'
const SESSION_NAME_KEY = 'cmkb-session-name'

function loadPersistedMessages() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved ? JSON.parse(saved) : []
  } catch {
    return []
  }
}

function deriveSessionName(messages) {
  const firstUserMsg = messages.find(m => m.role === 'user')
  if (!firstUserMsg) return null
  const text = firstUserMsg.content
  // Truncate to ~50 chars at a word boundary
  if (text.length <= 50) return text
  const trimmed = text.slice(0, 50)
  const lastSpace = trimmed.lastIndexOf(' ')
  return (lastSpace > 20 ? trimmed.slice(0, lastSpace) : trimmed) + '...'
}

export default function App() {
  const [messages, setMessages] = useState(loadPersistedMessages)
  const [filters, setFilters] = useState({})
  const [health, setHealth] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const [lastFailedQuestion, setLastFailedQuestion] = useState(null)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const { submitQuery, checkHealth, loading, error } = useQuery()
  const { dark, toggle: toggleTheme } = useTheme()

  // Persist messages to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages))
      const name = deriveSessionName(messages)
      if (name) localStorage.setItem(SESSION_NAME_KEY, name)
    } catch { /* quota exceeded — ignore */ }
  }, [messages])

  // Check health on mount
  useEffect(() => {
    checkHealth().then(h => h && setHealth(h))
  }, [])

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e) {
      // Cmd/Ctrl+K → focus input
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
      }
      // Escape → close modals/sidebar
      if (e.key === 'Escape') {
        if (sourcesOpen) setSourcesOpen(false)
        else if (sidebarOpen) setSidebarOpen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [sourcesOpen, sidebarOpen])

  // Build conversation context from message history (last 3 Q&A pairs)
  function getConversationContext() {
    const pairs = []
    for (let i = 0; i < messages.length - 1; i++) {
      if (messages[i].role === 'user' && messages[i + 1]?.role === 'assistant') {
        pairs.push({
          question: messages[i].content,
          answer: messages[i + 1].content,
        })
      }
    }
    return pairs.slice(-3)
  }

  const handleSubmit = useCallback(async (question) => {
    setLastFailedQuestion(null)
    const userMsg = { role: 'user', content: question, id: Date.now() }
    setMessages(prev => [...prev, userMsg])

    const context = getConversationContext()
    const data = await submitQuery(question, filters, context)

    if (data) {
      const assistantMsg = {
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        verification: data.verification,
        metadata: data.metadata,
        follow_up_questions: data.follow_up_questions,
        graph_data: data.graph_data,
        question: question,
        id: Date.now(),
      }
      setMessages(prev => [...prev, assistantMsg])
    } else {
      setLastFailedQuestion(question)
    }
  }, [filters, submitQuery])

  function handleRetry() {
    if (!lastFailedQuestion) return
    // Remove the last user message (the failed one) first
    setMessages(prev => {
      const last = prev[prev.length - 1]
      if (last?.role === 'user' && last.content === lastFailedQuestion) {
        return prev.slice(0, -1)
      }
      return prev
    })
    handleSubmit(lastFailedQuestion)
  }

  function handleClearChat() {
    setMessages([])
    setLastFailedQuestion(null)
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(SESSION_NAME_KEY)
  }

  const sessionName = deriveSessionName(messages)

  return (
    <div className="flex h-screen bg-white dark:bg-slate-900">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 lg:static lg:z-auto transition-transform duration-200 ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
      }`}>
        <Sidebar
          filters={filters}
          onFiltersChange={setFilters}
          health={health}
          dark={dark}
          onToggleTheme={toggleTheme}
          onMobileClose={() => setSidebarOpen(false)}
        />
      </div>

      {/* Main area */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="shrink-0 border-b border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-1.5 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 truncate">
              {sessionName || 'Supply Chain Analyst'}
            </h2>
            {sessionName && (
              <p className="text-[10px] text-slate-400 dark:text-slate-500">
                Supply Chain Analyst
              </p>
            )}
          </div>
          <div className="flex-1" />
          {/* Keyboard shortcut hint */}
          <span className="hidden sm:inline text-[10px] text-slate-400 dark:text-slate-600 border border-slate-200 dark:border-slate-700 rounded px-1.5 py-0.5">
            <kbd className="font-mono">⌘K</kbd>
          </span>
          {/* Sources Library button */}
          <button
            onClick={() => setSourcesOpen(true)}
            className="text-xs px-3 py-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors font-medium flex items-center gap-1.5"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <span className="hidden sm:inline">Sources</span>
          </button>
          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              className="text-xs px-3 py-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors font-medium"
            >
              Clear chat
            </button>
          )}
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <WelcomeScreen onSelectQuery={handleSubmit} />
          ) : (
            <div className="max-w-4xl mx-auto p-4 space-y-4">
              {messages.map(msg => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  onFollowUp={handleSubmit}
                  dark={dark}
                />
              ))}
              {loading && <LoadingIndicator />}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Error banner with retry */}
        {error && !loading && (
          <div className="mx-4 mb-2 px-4 py-2.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-3">
            <svg className="w-4 h-4 text-red-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <span className="text-xs text-red-600 dark:text-red-400 flex-1">{error}</span>
            {lastFailedQuestion && (
              <button
                onClick={handleRetry}
                className="text-xs px-3 py-1 bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 rounded-md hover:bg-red-200 dark:hover:bg-red-900/60 font-medium transition-colors flex items-center gap-1"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Retry
              </button>
            )}
          </div>
        )}

        {/* Input */}
        <ChatInput ref={inputRef} onSubmit={handleSubmit} loading={loading} />
      </main>

      {/* Sources Library Modal */}
      <SourcesLibrary open={sourcesOpen} onClose={() => setSourcesOpen(false)} />
    </div>
  )
}
