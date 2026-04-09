import { useState } from 'react'

const DOC_TYPES = [
  { value: '', label: 'All Documents' },
  { value: 'usgs_mcs', label: 'USGS MCS Reports' },
  { value: 'gao_report', label: 'GAO Reports' },
  { value: 'crs_report', label: 'CRS Reports' },
  { value: 'doe_report', label: 'DOE Reports' },
  { value: 'dpa_announcement', label: 'DPA Announcements' },
  { value: 'industry', label: 'Industry' },
  { value: 'regulatory', label: 'Regulatory' },
]

export default function Sidebar({ filters, onFiltersChange, health, dark, onToggleTheme, onMobileClose }) {
  const [materialsInput, setMaterialsInput] = useState(
    filters.materials ? filters.materials.join(', ') : ''
  )

  function handleMaterialsBlur() {
    const materials = materialsInput
      .split(',')
      .map(m => m.trim())
      .filter(Boolean)
    onFiltersChange({ ...filters, materials: materials.length ? materials : undefined })
  }

  function handleDocTypeChange(e) {
    const val = e.target.value
    onFiltersChange({
      ...filters,
      doc_types: val ? [val] : undefined,
    })
  }

  return (
    <aside className="w-72 shrink-0 border-r border-[var(--color-border,#e2e8f0)] dark:border-slate-700 bg-slate-50 dark:bg-slate-900 flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="p-5 border-b border-[var(--color-border,#e2e8f0)] dark:border-slate-700">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-bold text-slate-900 dark:text-slate-100 leading-tight">
            Critical Materials<br />Knowledge Base
          </h1>
          <button
            onClick={onMobileClose}
            className="lg:hidden p-1 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 leading-relaxed">
          Hybrid RAG + Knowledge Graph powered supply chain intelligence
        </p>
      </div>

      {/* Filters */}
      <div className="p-5 flex-1">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
          Filters
        </h2>

        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
          Materials
        </label>
        <input
          type="text"
          value={materialsInput}
          onChange={e => setMaterialsInput(e.target.value)}
          onBlur={handleMaterialsBlur}
          onKeyDown={e => e.key === 'Enter' && handleMaterialsBlur()}
          placeholder="tungsten, nickel, cobalt"
          className="w-full px-3 py-2 text-sm bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 text-slate-900 dark:text-slate-100 placeholder:text-slate-400"
        />

        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5 mt-4">
          Document Type
        </label>
        <select
          value={filters.doc_types?.[0] || ''}
          onChange={handleDocTypeChange}
          className="w-full px-3 py-2 text-sm bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 text-slate-900 dark:text-slate-100"
        >
          {DOC_TYPES.map(dt => (
            <option key={dt.value} value={dt.value}>{dt.label}</option>
          ))}
        </select>
      </div>

      {/* Footer */}
      <div className="p-5 border-t border-[var(--color-border,#e2e8f0)] dark:border-slate-700 space-y-3">
        {/* Theme toggle */}
        <button
          onClick={onToggleTheme}
          className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors"
        >
          {dark ? (
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          )}
          {dark ? 'Light Mode' : 'Dark Mode'}
        </button>

        {/* System status */}
        {health && (
          <div className="text-xs text-slate-500 dark:text-slate-500 space-y-0.5">
            <div className="flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full ${health.status === 'ok' ? 'bg-emerald-500' : 'bg-red-500'}`} />
              <span>{health.status === 'ok' ? 'System Online' : 'System Error'}</span>
            </div>
            <div className="pl-3">{health.document_count} documents &middot; {health.chunk_count} chunks</div>
          </div>
        )}
      </div>
    </aside>
  )
}
