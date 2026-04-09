import { useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || ''

export function useQuery() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function submitQuery(question, filters = {}, conversationContext = []) {
    setLoading(true)
    setError(null)

    try {
      const body = {
        question,
        filters,
        include_sources: true,
      }
      if (conversationContext.length > 0) {
        body.conversation_context = conversationContext
      }

      const res = await fetch(`${API_BASE}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        // Try to surface the server-provided detail (e.g. the
        // friendly 429 rate-limit message) instead of a generic
        // "API error: 429" that gives the user no guidance.
        let detail = null
        try {
          const body = await res.json()
          detail = body?.detail
        } catch { /* body wasn't JSON — fall through to generic */ }

        if (res.status === 429) {
          throw new Error(
            detail || 'Too many requests. Please wait a few minutes before trying again.'
          )
        }
        throw new Error(detail || `API error: ${res.status} ${res.statusText}`)
      }

      const data = await res.json()
      return data
    } catch (err) {
      setError(err.message)
      return null
    } finally {
      setLoading(false)
    }
  }

  async function checkHealth() {
    try {
      const res = await fetch(`${API_BASE}/api/health`)
      if (!res.ok) return null
      return await res.json()
    } catch {
      return null
    }
  }

  return { submitQuery, checkHealth, loading, error }
}
