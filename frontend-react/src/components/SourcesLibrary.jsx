import { useState, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || ''

export default function SourcesLibrary({ open, onClose }) {
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (open && sources.length === 0) {
      setLoading(true)
      fetch(`${API_BASE}/api/sources`)
        .then(r => r.json())
        .then(data => setSources(data))
        .catch(() => {})
        .finally(() => setLoading(false))
    }
  }, [open])

  if (!open) return null

  // Group by type based on filename patterns
  function getCategory(name) {
    if (name.startsWith('mcs')) return 'USGS Mineral Commodity Summaries'
    if (name.startsWith('GAO')) return 'GAO Reports'
    if (name.startsWith('R4') || name.startsWith('IF')) return 'CRS Reports'
    if (name.startsWith('doe-')) return 'DOE Reports'
    if (name.startsWith('dpa-')) return 'DPA Title III Announcements'
    if (name.startsWith('dfars')) return 'Regulatory'
    return 'Industry Sources'
  }

  const grouped = {}
  sources.forEach(s => {
    const cat = getCategory(s.name)
    if (!grouped[cat]) grouped[cat] = []
    grouped[cat].push(s)
  })

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-white dark:bg-slate-900 rounded-t-2xl sm:rounded-2xl shadow-xl border border-slate-200 dark:border-slate-700 w-full sm:max-w-2xl max-h-[85vh] sm:max-h-[80vh] overflow-hidden flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Source Document Library
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {sources.length} documents indexed — click to view original source
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {loading ? (
            <div className="text-center py-8 text-sm text-slate-500">Loading sources...</div>
          ) : (
            Object.entries(grouped).map(([category, docs]) => (
              <div key={category}>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
                  {category}
                </h3>
                <div className="space-y-1.5">
                  {docs.map((doc, i) => (
                    <div key={i} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 group">
                      {/* File icon */}
                      <svg className="w-4 h-4 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                      <span className="text-sm text-slate-700 dark:text-slate-300 flex-1 truncate">
                        {doc.name}
                      </span>
                      {doc.url ? (
                        <a
                          href={doc.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs px-2.5 py-1 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-md hover:bg-blue-100 dark:hover:bg-blue-900/50 font-medium transition-colors opacity-0 group-hover:opacity-100"
                        >
                          View Source ↗
                        </a>
                      ) : (
                        <span className="text-xs text-slate-400 dark:text-slate-500">
                          Local file
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
