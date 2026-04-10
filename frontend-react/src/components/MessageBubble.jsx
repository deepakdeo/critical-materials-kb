import { useState, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import ConfidenceBar from './ConfidenceBar'
import ExportButton from './ExportButton'
import FollowUpQuestions from './FollowUpQuestions'
import GraphVisualization from './GraphVisualization'

/** Highlight inline citations — clicking scrolls to sources */
function HighlightCitations({ children, onCitationClick }) {
  if (typeof children !== 'string') return children
  const parts = children.split(/(\[[^\]]*\.(?:pdf|html|txt)[^\]]*\]|\[Knowledge Graph[^\]]*\])/g)
  if (parts.length === 1) return children
  return parts.map((part, i) =>
    part.match(/^\[.*\]$/) ? (
      <button
        key={i}
        onClick={() => onCitationClick?.(part)}
        className="inline-block text-xs font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-1.5 py-0.5 rounded mx-0.5 hover:bg-blue-100 dark:hover:bg-blue-900/50 cursor-pointer transition-colors align-baseline"
        title="View source"
      >
        {part}
      </button>
    ) : part
  )
}

function VerificationBadge({ verification }) {
  if (!verification) return null
  const pass = verification.verdict === 'PASS'
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${
      pass
        ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
        : 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
    }`}>
      {pass ? (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
        </svg>
      )}
      Verified: {verification.verdict}
      {verification.severity !== 'none' && ` (${verification.severity})`}
    </span>
  )
}

function SourceIcon({ name }) {
  if (name === 'Knowledge Graph') {
    return (
      <svg className="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
      </svg>
    )
  }
  if (name.endsWith('.pdf')) {
    return (
      <svg className="w-3.5 h-3.5 text-red-500 dark:text-red-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
      </svg>
    )
  }
  return (
    <svg className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  )
}

/** Parse "p.204" or "p.199,200" into the first page number, or null. */
function extractFirstPage(pageStr) {
  if (!pageStr) return null
  const match = pageStr.match(/p\.(\d+)/)
  return match ? parseInt(match[1], 10) : null
}

function SourcesList({ sources, expanded, onToggle, highlightIndex, expandedChunk, onToggleChunk }) {
  if (!sources || sources.length === 0) return null

  return (
    <div className="mt-3">
      <button
        onClick={onToggle}
        className="flex items-center gap-1.5 text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
      >
        <svg className={`w-3.5 h-3.5 transition-transform ${expanded ? 'rotate-90' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        Sources ({sources.length})
      </button>
      {expanded && (
        <div className="mt-2 space-y-1 pl-5">
          {sources.map((s, i) => (
            <div key={i}>
              <div
                className={`flex items-start gap-2 text-xs px-2 py-1.5 rounded-lg transition-all cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 ${
                  highlightIndex === i
                    ? 'bg-blue-50 dark:bg-blue-900/20 ring-1 ring-blue-200 dark:ring-blue-800'
                    : ''
                }`}
                onClick={() => onToggleChunk(i)}
              >
                <SourceIcon name={s.name} />
                <div className="min-w-0 flex-1 break-words">
                  <span className="font-medium text-slate-700 dark:text-slate-300">{s.name}</span>
                  {s.page && <span className="ml-1.5 text-slate-500 dark:text-slate-400">{s.page}</span>}
                  {s.section && s.section !== 'Knowledge Graph' && (
                    <span className="ml-1.5 text-slate-400 dark:text-slate-500">— {s.section}</span>
                  )}
                  {s.name === 'Knowledge Graph' && (
                    <span className="ml-1.5 text-indigo-500 dark:text-indigo-400 font-normal">
                      (supply chain graph data)
                    </span>
                  )}
                </div>
                {/* External link */}
                {s.source_url && (
                  <a
                    href={s.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={e => e.stopPropagation()}
                    className="shrink-0 text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                    title="View original document"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                )}
                {/* Expand indicator */}
                {s.chunk_text && (
                  <svg className={`w-3 h-3 text-slate-400 shrink-0 transition-transform ${expandedChunk === i ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                )}
              </div>
              {/* Chunk text preview + deep-link to original PDF page */}
              {expandedChunk === i && s.chunk_text && (
                <div className="ml-7 mt-1 mb-2 px-3 py-2 bg-slate-100 dark:bg-slate-800 rounded-lg text-xs text-slate-600 dark:text-slate-400 leading-relaxed border-l-2 border-blue-300 dark:border-blue-600">
                  <div className="whitespace-pre-wrap">
                    {s.chunk_text}
                    {s.chunk_text.length >= 500 && <span className="text-slate-400">...</span>}
                  </div>
                  {s.source_url && s.source_url.includes('#page=') && (
                    <a
                      href={s.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-medium transition-colors"
                    >
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                      Open page {extractFirstPage(s.page)} in source PDF
                    </a>
                  )}
                  {s.source_url && !s.source_url.includes('#page=') && s.name !== 'Knowledge Graph' && (
                    <a
                      href={s.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 text-[11px] font-medium transition-colors"
                    >
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                      Open original source
                    </a>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function QueryMetadata({ metadata }) {
  const [expanded, setExpanded] = useState(false)
  if (!metadata) return null

  const fromCache = metadata.from_cache === true
  const formatLatency = (ms) =>
    ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`

  return (
    <div className="mt-2">
      <div className="flex items-center gap-2">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
        >
          <svg className={`w-3.5 h-3.5 transition-transform ${expanded ? 'rotate-90' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          Query Details
        </button>
        {fromCache && (
          <span
            title="This response was served from the 24h Supabase-backed query cache — no LLM calls were made."
            className="inline-flex items-center gap-1 rounded-full bg-blue-50 dark:bg-blue-950/40 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800"
          >
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
            </svg>
            Cached
          </span>
        )}
      </div>
      {expanded && (
        <div className="mt-2 pl-5 flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
          {metadata.query_type && (
            <div>
              <span className="text-slate-400 dark:text-slate-500">Type:</span>{' '}
              <span className="font-medium text-slate-600 dark:text-slate-300">{metadata.query_type}</span>
            </div>
          )}
          {metadata.retrieval_method && (
            <div>
              <span className="text-slate-400 dark:text-slate-500">Retrieval:</span>{' '}
              <span className="font-medium text-slate-600 dark:text-slate-300">{metadata.retrieval_method}</span>
            </div>
          )}
          {metadata.chunks_retrieved != null && (
            <div>
              <span className="text-slate-400 dark:text-slate-500">Chunks:</span>{' '}
              <span className="font-medium text-slate-600 dark:text-slate-300">
                {metadata.chunks_retrieved} → {metadata.chunks_after_rerank}
              </span>
            </div>
          )}
          {metadata.latency_ms != null && (
            <div>
              <span className="text-slate-400 dark:text-slate-500">Latency:</span>{' '}
              <span className="font-medium text-slate-600 dark:text-slate-300">
                {formatLatency(metadata.latency_ms)}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function MessageBubble({ message, onFollowUp, dark }) {
  const isUser = message.role === 'user'
  const [sourcesExpanded, setSourcesExpanded] = useState(false)
  const [highlightIndex, setHighlightIndex] = useState(-1)
  const [expandedChunk, setExpandedChunk] = useState(-1)
  const sourcesRef = useRef(null)

  function handleCitationClick(citationText) {
    const match = citationText.match(/\[([^\],]+)/)
    if (!match) return

    const sourceName = match[1].trim()
    const sources = message.sources || []

    const idx = sources.findIndex(s =>
      s.name.toLowerCase().includes(sourceName.toLowerCase()) ||
      sourceName.toLowerCase().includes(s.name.toLowerCase())
    )

    setSourcesExpanded(true)
    setHighlightIndex(idx >= 0 ? idx : -1)
    if (idx >= 0) setExpandedChunk(idx)

    setTimeout(() => {
      sourcesRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }, 100)
    setTimeout(() => setHighlightIndex(-1), 3000)
  }

  const markdownComponents = {
    p: ({ children }) => (
      <p>
        {Array.isArray(children)
          ? children.map((c, i) => <HighlightCitations key={i} onCitationClick={handleCitationClick}>{c}</HighlightCitations>)
          : <HighlightCitations onCitationClick={handleCitationClick}>{children}</HighlightCitations>
        }
      </p>
    ),
    li: ({ children }) => (
      <li>
        {Array.isArray(children)
          ? children.map((c, i) => <HighlightCitations key={i} onCitationClick={handleCitationClick}>{c}</HighlightCitations>)
          : <HighlightCitations onCitationClick={handleCitationClick}>{children}</HighlightCitations>
        }
      </li>
    ),
  }

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] sm:max-w-2xl px-3 sm:px-4 py-2.5 sm:py-3 bg-blue-600 text-white rounded-2xl rounded-br-md text-sm leading-relaxed break-words">
          {message.content}
        </div>
      </div>
    )
  }

  const { content, sources, verification, metadata, follow_up_questions, graph_data } = message
  return (
    <div className="flex justify-start">
      <div className="max-w-3xl w-full">
        <div className="px-3 sm:px-4 py-2.5 sm:py-3 bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-2xl rounded-bl-md">
          {/* Fallback banner — shown when CRAG verification fails and the
              system returned a corpus-gap explanation instead of an answer */}
          {metadata?.is_fallback && (
            <div className="mb-3 px-3 py-2 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 text-xs text-amber-900 dark:text-amber-200 flex items-start gap-2">
              <span className="mt-0.5">⚠</span>
              <div>
                <div className="font-semibold">This question could not be answered with high confidence.</div>
                <div className="mt-0.5 opacity-90">The response below explains what the corpus does cover on this topic and suggests reformulations you can try.</div>
              </div>
            </div>
          )}

          {/* Answer */}
          <div className="answer-content text-sm text-slate-800 dark:text-slate-200">
            <ReactMarkdown components={markdownComponents}>{content}</ReactMarkdown>
          </div>

          {/* Verification + Confidence + Export */}
          {(verification || metadata?.confidence != null) && (
            <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700 flex flex-wrap items-center gap-2 sm:gap-3">
              <VerificationBadge verification={verification} />
              <ConfidenceBar confidence={metadata?.confidence} />
              <div className="flex-1" />
              <ExportButton message={{ ...message, question: message.question }} />
            </div>
          )}

          {/* Graph Visualization */}
          <GraphVisualization graphData={graph_data} dark={dark} />

          {/* Sources */}
          <div ref={sourcesRef}>
            <SourcesList
              sources={sources}
              expanded={sourcesExpanded}
              onToggle={() => setSourcesExpanded(!sourcesExpanded)}
              highlightIndex={highlightIndex}
              expandedChunk={expandedChunk}
              onToggleChunk={i => setExpandedChunk(expandedChunk === i ? -1 : i)}
            />
          </div>

          {/* Metadata */}
          <QueryMetadata metadata={metadata} />

          {/* Follow-up questions */}
          <FollowUpQuestions questions={follow_up_questions} onSelect={onFollowUp} />
        </div>
      </div>
    </div>
  )
}
