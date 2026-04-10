import { useEffect, useState } from 'react'

/**
 * Skeleton loader shown while a query is in flight.
 *
 * After 5 seconds we assume the request has hit a cold Render
 * container and show a friendly "warming up" notice so users don't
 * think the app has hung. The free-tier backend can take up to ~60s
 * to wake from idle, and the initial message ingestion pipeline adds
 * another 10-20s on top of that. Without this notice, a first-time
 * visitor who clicks an example query cold has no idea whether to
 * wait or give up.
 */
export default function LoadingIndicator() {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const startedAt = Date.now()
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000))
    }, 500)
    return () => clearInterval(interval)
  }, [])

  const isWarmingUp = elapsed >= 5
  const statusMessage = isWarmingUp
    ? 'Warming up the backend — cold start can take up to 60s.'
    : 'Searching documents and knowledge graph...'

  return (
    <div className="flex justify-start">
      <div className="max-w-3xl w-full">
        <div className="px-4 py-4 bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-2xl rounded-bl-md space-y-3">
          {/* Status line with animated dots */}
          <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:0ms]" />
              <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:150ms]" />
              <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:300ms]" />
            </div>
            <span className={isWarmingUp ? 'text-amber-600 dark:text-amber-400' : ''}>
              {statusMessage}
            </span>
            {elapsed >= 3 && (
              <span className="ml-auto text-xs tabular-nums text-slate-400 dark:text-slate-500">
                {elapsed}s
              </span>
            )}
          </div>

          {/* Cold-start explainer — only shown once we know it's slow */}
          {isWarmingUp && (
            <div className="text-xs text-slate-500 dark:text-slate-400 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/50 rounded-lg px-3 py-2 leading-relaxed">
              The backend runs on a free hosting tier that sleeps after
              15 minutes of inactivity. Once it is awake, subsequent
              queries take 5-15 seconds, and repeat questions are
              served from a 24h cache in under 200ms.
            </div>
          )}

          {/* Skeleton lines */}
          <div className="space-y-2.5 animate-pulse">
            <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded-full w-full" />
            <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded-full w-11/12" />
            <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded-full w-4/5" />
            <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded-full w-9/12" />
            <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded-full w-3/4" />
          </div>

          {/* Skeleton metadata bar */}
          <div className="pt-2 border-t border-slate-200 dark:border-slate-700 flex items-center gap-3 animate-pulse">
            <div className="h-5 w-28 bg-slate-200 dark:bg-slate-700 rounded-full" />
            <div className="h-2 w-20 bg-slate-200 dark:bg-slate-700 rounded-full" />
            <div className="flex-1" />
            <div className="h-4 w-14 bg-slate-200 dark:bg-slate-700 rounded" />
          </div>
        </div>
      </div>
    </div>
  )
}
