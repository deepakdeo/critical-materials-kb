export default function ConfidenceBar({ confidence }) {
  if (confidence == null) return null

  const pct = Math.round(confidence * 100)
  const color =
    pct >= 80 ? 'bg-emerald-500' :
    pct >= 60 ? 'bg-amber-500' :
    'bg-red-500'

  const label =
    pct >= 80 ? 'High' :
    pct >= 60 ? 'Medium' :
    'Low'

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-500 dark:text-slate-400 shrink-0">
        Confidence:
      </span>
      <div className="flex-1 max-w-24 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
        {pct}% {label}
      </span>
    </div>
  )
}
