function ReviewToggle({ checked, onChange, label, disabled = false }) {
  return (
    <label style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', cursor: disabled ? 'default' : 'pointer' }}>
      <input type="checkbox" checked={checked} onChange={onChange} disabled={disabled} />
      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', fontWeight: 600 }}>{label}</span>
    </label>
  )
}

function normalizeText(value) {
  return (value || '').toLowerCase()
}

function countNewMatches(before, after, terms) {
  const beforeText = normalizeText(before)
  const afterText = normalizeText(after)

  return terms.filter((term) => {
    const token = normalizeText(term)
    return token && !beforeText.includes(token) && afterText.includes(token)
  }).length
}

function estimateImpact(before, after, originalScore) {
  if (!originalScore) return 1

  const skillMatches = countNewMatches(before, after, originalScore.missing_skills || [])
  const keywordMatches = countNewMatches(before, after, originalScore.missing_keywords || [])
  const points = (skillMatches * 2) + keywordMatches
  return Math.max(1, Math.min(points || 1, 8))
}

function ImpactBadge({ points }) {
  return (
    <span
      style={{
        marginLeft: 'auto',
        fontSize: 'var(--text-xs)',
        fontWeight: 700,
        color: 'var(--success)',
        border: '1px solid rgba(61, 217, 176, 0.35)',
        background: 'rgba(61, 217, 176, 0.08)',
        borderRadius: '999px',
        padding: '4px 10px',
        whiteSpace: 'nowrap',
      }}
    >
      Est. +{points} pts
    </span>
  )
}

function DiffView({
  optimization,
  originalScore,
  reviewMode = false,
  selection = null,
  onApplyAllContent,
  onClearContent,
  onApplyAllSkills,
  onClearSkills,
  onToggleSummary,
  onToggleSkills,
  onToggleSkill,
  onToggleExperience,
  applyingChanges = false,
}) {
  if (!optimization) return null

  const { experience_rewrites = [], summary_rewrite = '', skills_to_add = [], keywords_to_inject = [] } = optimization
  const manualSkills = selection
    ? selection.approved_skills_to_add.filter((skill) => !skills_to_add.includes(skill))
    : []

  return (
    <section className="diff-section" aria-label="Resume changes">
      <header className="section-header">
        <h2 className="section-title">
          <span aria-hidden="true">📝</span> Changes Applied
        </h2>
        <p className="section-subtitle">Here's exactly what was modified in your resume</p>
      </header>

      {reviewMode && selection && (
        <div
          style={{
            display: 'flex',
            gap: '12px',
            flexWrap: 'wrap',
            marginBottom: 'var(--space-6)',
          }}
        >
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onApplyAllContent}
            disabled={applyingChanges}
            style={{ padding: '10px 16px', fontSize: 'var(--text-sm)' }}
          >
            Apply All Content
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClearContent}
            disabled={applyingChanges}
            style={{ padding: '10px 16px', fontSize: 'var(--text-sm)' }}
          >
            Clear Content
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onApplyAllSkills}
            disabled={applyingChanges}
            style={{ padding: '10px 16px', fontSize: 'var(--text-sm)' }}
          >
            Apply All Technical Skills
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClearSkills}
            disabled={applyingChanges}
            style={{ padding: '10px 16px', fontSize: 'var(--text-sm)' }}
          >
            Clear Technical Skills
          </button>
        </div>
      )}

      {/* Summary Rewrite */}
      {summary_rewrite && (
        <article className="glass-card diff-card" style={{ marginBottom: 'var(--space-6)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
            <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 700, color: 'var(--text-accent)', margin: 0 }}>
              Professional Summary
            </h3>
            <ImpactBadge points={estimateImpact('', summary_rewrite, originalScore)} />
          </div>
          {reviewMode && selection && (
            <div style={{ marginBottom: 'var(--space-3)' }}>
              <ReviewToggle
                checked={selection.apply_summary}
                onChange={onToggleSummary}
                disabled={applyingChanges}
                label="Apply this summary rewrite"
              />
            </div>
          )}
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
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
                <p className="diff-label original" style={{ margin: 0 }}>— Original</p>
                <ImpactBadge points={estimateImpact(rewrite.original, rewrite.replacement, originalScore)} />
              </div>
              {reviewMode && selection && (
                <div style={{ marginBottom: 'var(--space-3)' }}>
                  <ReviewToggle
                    checked={selection.approved_experience_indices.includes(i)}
                    onChange={() => onToggleExperience?.(i)}
                    disabled={applyingChanges}
                    label="Apply this bullet rewrite"
                  />
                </div>
              )}
              <p className="diff-text original">{rewrite.original}</p>
              <p className="diff-label optimized" style={{ marginTop: 'var(--space-3)' }}>+ Optimized</p>
              <p className="diff-text optimized">{rewrite.replacement}</p>
            </div>
          ))}
        </article>
      )}

      {/* Skills & Keywords Added */}
      {(skills_to_add.length > 0 || manualSkills.length > 0 || keywords_to_inject.length > 0) && (
        <article className="glass-card diff-card">
          <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 700, marginBottom: 'var(--space-4)', color: 'var(--text-accent)' }}>
            Added Skills &amp; Keywords
          </h3>
          {reviewMode && selection && skills_to_add.length > 0 && (
            <div style={{ marginBottom: 'var(--space-4)' }}>
              <ReviewToggle
                checked={selection.apply_skills}
                onChange={onToggleSkills}
                disabled={applyingChanges}
                label="Apply skills section cleanup and approved skill additions"
              />
            </div>
          )}

          {(skills_to_add.length > 0 || manualSkills.length > 0) && (
            <div style={{ marginBottom: 'var(--space-4)' }}>
              <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-2)' }}>
                SKILLS ADDED
              </p>
              <div className="tag-list">
                {[...skills_to_add, ...manualSkills].map((skill, i) => {
                  const checked = selection?.approved_skills_to_add.includes(skill) ?? true
                  return (
                    <label
                      key={i}
                      className="tag tag-added"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '8px',
                        opacity: reviewMode && selection && !selection.apply_skills ? 0.55 : 1,
                        cursor: reviewMode ? 'pointer' : 'default',
                      }}
                    >
                      {reviewMode && (
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => onToggleSkill?.(skill)}
                          disabled={applyingChanges || !selection?.apply_skills}
                        />
                      )}
                      <span>+ {skill} · Est. +{estimateImpact('', skill, originalScore)}</span>
                    </label>
                  )
                })}
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
                  <span key={i} className="tag tag-added">+ {kw} · Est. +{estimateImpact('', kw, originalScore)}</span>
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
