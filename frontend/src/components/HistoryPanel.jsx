function formatWhen(value) {
  if (!value) return 'Unknown time'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function HistoryPanel({ items, loading, activeId, onOpen, onDelete, deletingId }) {
  return (
    <section className="glass-card history-panel" aria-label="Saved optimization history">
      <div className="history-panel-header">
        <div>
          <span className="history-eyebrow">Saved runs</span>
          <h2 className="history-title">Optimization history</h2>
        </div>
        <span className="history-count">{items.length}</span>
      </div>

      <p className="history-subtitle">
        Open any previous run to review its ATS score, applied changes, and downloadable result.
      </p>

      {loading ? (
        <div className="history-empty">Loading saved runs...</div>
      ) : items.length === 0 ? (
        <div className="history-empty">
          Your saved optimizations will appear here after the first run.
        </div>
      ) : (
        <div className="history-list">
          {items.map((item) => {
            const improvement = item.optimized_score - item.original_score
            return (
              <article
                key={item.id}
                className={`history-item ${activeId === item.id ? 'active' : ''}`}
              >
                <div className="history-item-top">
                  <div>
                    <h3 className="history-item-title">{item.company_name}</h3>
                    <p className="history-item-meta">
                      {item.provider} · {item.model || 'default model'}
                    </p>
                  </div>
                  <span className={`history-status history-status--${item.review_applied ? 'final' : 'draft'}`}>
                    {item.review_applied ? 'Final' : 'Draft'}
                  </span>
                </div>

                <div className="history-score-row">
                  <span>{item.original_score} → {item.optimized_score}</span>
                  <span className={improvement >= 0 ? 'history-improvement' : 'history-regression'}>
                    {improvement >= 0 ? `+${improvement}` : improvement} pts
                  </span>
                </div>

                <p className="history-item-time">{formatWhen(item.created_at)}</p>

                <div className="history-actions">
                  <button
                    type="button"
                    className="btn btn-secondary history-open-button"
                    onClick={() => onOpen(item.id)}
                  >
                    {activeId === item.id ? 'Viewing run' : 'Open run'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary history-delete-button"
                    onClick={() => onDelete?.(item.id)}
                    disabled={deletingId === item.id}
                  >
                    {deletingId === item.id
                      ? 'Deleting...'
                      : (item.review_applied ? 'Delete run' : 'Delete draft')}
                  </button>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}

export default HistoryPanel
