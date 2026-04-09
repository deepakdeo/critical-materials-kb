export default function LoadingIndicator() {
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
            <span>Searching documents and knowledge graph...</span>
          </div>

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
