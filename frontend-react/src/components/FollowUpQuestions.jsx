export default function FollowUpQuestions({ questions, onSelect }) {
  if (!questions || questions.length === 0) return null

  return (
    <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
      <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">
        Follow-up questions
      </p>
      <div className="flex flex-wrap gap-2">
        {questions.map((q, i) => (
          <button
            key={i}
            onClick={() => onSelect(q)}
            className="text-xs px-3 py-1.5 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 rounded-full hover:border-blue-300 dark:hover:border-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors text-left"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}
