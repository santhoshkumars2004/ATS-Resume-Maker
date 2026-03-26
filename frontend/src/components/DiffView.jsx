function DiffView({ optimization }) {
  if (!optimization) return null

  const { experience_rewrites = [], summary_rewrite = '', skills_to_add = [], keywords_to_inject = [] } = optimization

  return (
    <section className="diff-section" aria-label="Resume changes">
      <header className="section-header">
        <h2 className="section-title">
          <span aria-hidden="true">📝</span> Changes Applied
        </h2>
        <p className="section-subtitle">Here's exactly what was modified in your resume</p>
      </header>

      {/* Summary Rewrite */}
      {summary_rewrite && (
        <article className="glass-card diff-card" style={{ marginBottom: 'var(--space-6)' }}>
          <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 700, marginBottom: 'var(--space-4)', color: 'var(--text-accent)' }}>
            Professional Summary
          </h3>
          <div className="diff-item">
            <p className="diff-label optimized">✨ Optimized</p>
            <p className="diff-text optimized">{summary_rewrite}</p>
          </div>
        </article>
      )}

      {/* Experience Rewrites */}
      {experience_rewrites.length > 0 && (
        <article className="glass-card diff-card" style={{ marginBottom: 'var(--space-6)' }}>
          <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 700, marginBottom: 'var(--space-4)', color: 'var(--text-accent)' }}>
            Experience Bullets
          </h3>
          {experience_rewrites.map((rewrite, i) => (
            <div key={i} className="diff-item">
              <p className="diff-label original">— Original</p>
              <p className="diff-text original">{rewrite.original}</p>
              <p className="diff-label optimized" style={{ marginTop: 'var(--space-3)' }}>+ Optimized</p>
              <p className="diff-text optimized">{rewrite.replacement}</p>
            </div>
          ))}
        </article>
      )}

      {/* Skills & Keywords Added */}
      {(skills_to_add.length > 0 || keywords_to_inject.length > 0) && (
        <article className="glass-card diff-card">
          <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 700, marginBottom: 'var(--space-4)', color: 'var(--text-accent)' }}>
            Added Skills &amp; Keywords
          </h3>

          {skills_to_add.length > 0 && (
            <div style={{ marginBottom: 'var(--space-4)' }}>
              <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-2)' }}>
                SKILLS ADDED
              </p>
              <div className="tag-list">
                {skills_to_add.map((skill, i) => (
                  <span key={i} className="tag tag-added">+ {skill}</span>
                ))}
              </div>
            </div>
          )}

          {keywords_to_inject.length > 0 && (
            <div>
              <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-2)' }}>
                KEYWORDS INJECTED
              </p>
              <div className="tag-list">
                {keywords_to_inject.map((kw, i) => (
                  <span key={i} className="tag tag-added">+ {kw}</span>
                ))}
              </div>
            </div>
          )}
        </article>
      )}
    </section>
  )
}

export default DiffView
