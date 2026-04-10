// Curated example questions spanning all six query categories and a
// cross-section of the corpus (tungsten, battery minerals, rare earths,
// gallium, DFARS, DOE critical materials list). Drawn from the golden
// eval set so first-time users see queries the pipeline handles well.
const EXAMPLE_QUERIES = [
  {
    category: 'Factual',
    text: 'What is the current U.S. import reliance for tungsten?',
  },
  {
    category: 'Factual',
    text: 'Which country is the largest global producer of tungsten?',
  },
  {
    category: 'Relational',
    text: 'Which U.S. companies produce tungsten powder?',
  },
  {
    category: 'Relational',
    text: 'Which DPA Title III awards have been made for critical battery minerals?',
  },
  {
    category: 'Analytical',
    text: 'If China cuts tungsten exports, which DoD applications would be affected?',
  },
  {
    category: 'Regulatory',
    text: 'What compliance requirements exist for tungsten in DoD contracts?',
  },
  {
    category: 'Comparative',
    text: 'How do U.S. and Chinese tungsten production levels compare?',
  },
  {
    category: 'Policy',
    text: 'How has U.S. critical materials policy evolved since 2020?',
  },
]

export default function WelcomeScreen({ onSelectQuery }) {
  return (
    <div className="flex-1 flex items-center justify-center p-4 sm:p-8">
      <div className="max-w-2xl w-full text-center">
        <div className="mb-4 sm:mb-6">
          <div className="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-3 sm:mb-4 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
            <svg className="w-6 h-6 sm:w-8 sm:h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m5.231 13.481L15 17.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v16.5c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9zm3.75 11.625a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
            </svg>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
            Critical Materials Intelligence
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed max-w-lg mx-auto">
            Ask questions about U.S. critical materials supply chains. Every answer is backed by
            source citations from government reports, verified for accuracy, and enriched with
            knowledge graph data.
          </p>
        </div>

        <div className="text-left">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-3 text-center">
            Try asking
          </h3>
          <div className="grid gap-2 sm:grid-cols-2">
            {EXAMPLE_QUERIES.map((q, i) => (
              <button
                key={i}
                onClick={() => onSelectQuery(q.text)}
                className="group text-left px-3 py-2.5 sm:px-4 sm:py-3 text-sm bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl hover:border-blue-300 dark:hover:border-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
              >
                <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 group-hover:text-blue-500 dark:group-hover:text-blue-400 mb-1">
                  {q.category}
                </div>
                <div className="text-slate-600 dark:text-slate-300 leading-snug">
                  {q.text}
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
