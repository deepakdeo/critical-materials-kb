import { useState } from 'react'

export default function ExportButton({ message }) {
  const [copied, setCopied] = useState(false)

  function buildMarkdown() {
    const { content, sources, verification, metadata } = message
    let md = `## Question\n${message.question || 'N/A'}\n\n`
    md += `## Answer\n${content}\n\n`

    if (verification) {
      md += `**Verification:** ${verification.verdict}`
      if (verification.severity !== 'none') md += ` (${verification.severity})`
      md += '\n\n'
    }

    if (sources && sources.length > 0) {
      md += `## Sources\n`
      sources.forEach((s, i) => {
        md += `${i + 1}. **${s.name}** ${s.page}`
        if (s.section) md += ` — ${s.section}`
        if (s.source_url) md += ` ([link](${s.source_url}))`
        md += '\n'
      })
      md += '\n'
    }

    if (metadata) {
      md += `---\n*Query type: ${metadata.query_type || 'N/A'}`
      md += ` | Retrieval: ${metadata.retrieval_method || 'N/A'}`
      md += ` | Confidence: ${metadata.confidence ? Math.round(metadata.confidence * 100) + '%' : 'N/A'}*\n`
    }

    return md
  }

  async function handleCopy() {
    const md = buildMarkdown()
    try {
      await navigator.clipboard.writeText(md)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback
      const textarea = document.createElement('textarea')
      textarea.value = md
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1 text-xs text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
      title="Copy answer as Markdown"
    >
      {copied ? (
        <>
          <svg className="w-3.5 h-3.5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span className="text-emerald-500">Copied!</span>
        </>
      ) : (
        <>
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          Export
        </>
      )}
    </button>
  )
}
