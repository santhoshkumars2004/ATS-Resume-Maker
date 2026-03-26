import DiffView from './DiffView'

function ScoreGauge({ score, label }) {
  const radius = 70
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference
  const tier = score >= 75 ? 'high' : score >= 50 ? 'medium' : 'low'

  return (
    <div className="score-gauge" role="meter" aria-valuenow={score} aria-valuemin={0} aria-valuemax={100} aria-label={`${label}: ${score} out of 100`}>
      <svg viewBox="0 0 160 160" aria-hidden="true">
        <circle className="score-gauge-track" cx="80" cy="80" r={radius} />
        <circle
          className={`score-gauge-fill ${tier}`}
          cx="80" cy="80" r={radius}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="score-value">
        <span className={`score-number ${tier}`}>{score}</span>
        <span className="score-label-text">/100</span>
      </div>
    </div>
  )
}

function BreakdownBar({ label, score }) {
  const tier = score >= 75 ? 'high' : score >= 50 ? 'medium' : 'low'

  return (
    <li className="breakdown-item">
      <div className="breakdown-header">
        <span className="breakdown-label">{label}</span>
        <span className={`breakdown-value ${tier}`} style={{ color: `var(--${tier === 'high' ? 'success' : tier === 'medium' ? 'warning' : 'danger'})` }}>
          {score}%
        </span>
      </div>
      <div className="breakdown-bar">
        <div
          className={`breakdown-fill ${tier}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </li>
  )
}

function ScoreDashboard({ results, onReset, apiBase }) {
  const { jd_analysis, original_score, optimized_score, optimization, pdf_filename, pdf_url, status, message } = results
  const improvement = optimized_score.overall_score - original_score.overall_score

  return (
    <div className="results-container">
      {/* Scores Comparison */}
      <section className="score-section" aria-label="ATS score comparison">
        <article className="glass-card score-card">
          <h2 className="score-title">Original Score</h2>
          <ScoreGauge score={original_score.overall_score} label="Original ATS Score" />
          <ul className="breakdown-list">
            <BreakdownBar label="Skills Match" score={original_score.skills_match_pct} />
            <BreakdownBar label="Keywords Match" score={original_score.keyword_match_pct} />
            <BreakdownBar label="Experience Relevance" score={original_score.experience_relevance_pct} />
          </ul>
        </article>

        <article className="glass-card score-card">
          <h2 className="score-title">Optimized Score</h2>
          <ScoreGauge score={optimized_score.overall_score} label="Optimized ATS Score" />
          <ul className="breakdown-list">
            <BreakdownBar label="Skills Match" score={optimized_score.skills_match_pct} />
            <BreakdownBar label="Keywords Match" score={optimized_score.keyword_match_pct} />
            <BreakdownBar label="Experience Relevance" score={optimized_score.experience_relevance_pct} />
          </ul>
          {improvement > 0 && (
            <div className="improvement-badge">
              📈 +{improvement} points improvement
            </div>
          )}
        </article>
      </section>

      {/* Skills Analysis */}
      <section className="glass-card" style={{ padding: 'var(--space-6)', marginBottom: 'var(--space-8)' }} aria-label="Skills analysis">
        <header className="section-header">
          <h2 className="section-title">
            <span aria-hidden="true">🎯</span> Skills Analysis
          </h2>
        </header>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-6)' }}>
          <div>
            <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              ✅ Matched Skills
            </p>
            <div className="tag-list">
              {original_score.matched_skills?.map((s, i) => (
                <span key={i} className="tag tag-matched">{s}</span>
              ))}
            </div>
          </div>
          <div>
            <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              ❌ Missing Skills
            </p>
            <div className="tag-list">
              {original_score.missing_skills?.map((s, i) => (
                <span key={i} className="tag tag-missing">{s}</span>
              ))}
            </div>
          </div>
        </div>

        {/* Keywords */}
        <div style={{ marginTop: 'var(--space-6)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-6)' }}>
          <div>
            <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              ✅ Matched Keywords
            </p>
            <div className="tag-list">
              {original_score.matched_keywords?.map((k, i) => (
                <span key={i} className="tag tag-matched">{k}</span>
              ))}
            </div>
          </div>
          <div>
            <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              ❌ Missing Keywords
            </p>
            <div className="tag-list">
              {original_score.missing_keywords?.map((k, i) => (
                <span key={i} className="tag tag-missing">{k}</span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Job Details */}
      <section className="glass-card" style={{ padding: 'var(--space-6)', marginBottom: 'var(--space-8)' }} aria-label="Job details">
        <header className="section-header">
          <h2 className="section-title">
            <span aria-hidden="true">🏢</span> {jd_analysis.job_title} at {jd_analysis.company}
          </h2>
          <p className="section-subtitle">
            {jd_analysis.location} · {jd_analysis.job_type} · {jd_analysis.experience_years}+ years
          </p>
        </header>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-6)' }}>
          <div>
            <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Required Skills
            </p>
            <div className="tag-list">
              {jd_analysis.required_skills?.map((s, i) => (
                <span key={i} className="tag" style={{ background: 'var(--bg-glass-strong)', color: 'var(--text-primary)', border: '1px solid var(--border-light)' }}>{s}</span>
              ))}
            </div>
          </div>
          <div>
            <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Tech Stack
            </p>
            <div className="tag-list">
              {jd_analysis.tech_stack?.map((t, i) => (
                <span key={i} className="tag" style={{ background: 'var(--bg-glass-strong)', color: 'var(--text-primary)', border: '1px solid var(--border-light)' }}>{t}</span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Diff View */}
      <DiffView optimization={optimization} />

      {/* Download / Actions */}
      <section className="download-section" aria-label="Download optimized resume">
        <article className="glass-card download-card">
          <div className="download-icon" aria-hidden="true">
            {pdf_filename ? '📄' : '📝'}
          </div>
          <h2 className="download-title">
            {pdf_filename ? 'Your Optimized Resume is Ready!' : 'Resume Modified'}
          </h2>
          <p className="download-subtitle">
            {pdf_filename
              ? `Score improved from ${original_score.overall_score} → ${optimized_score.overall_score} (+${improvement} points)`
              : (message || 'The modified .tex file has been saved. You can compile it manually.')
            }
          </p>

          <div style={{ display: 'flex', gap: 'var(--space-4)', justifyContent: 'center', flexWrap: 'wrap' }}>
            {pdf_filename && (
              <a
                href={`${apiBase}${pdf_url}`}
                className="btn btn-primary btn-large"
                download={pdf_filename}
                id="download-pdf-button"
              >
                <span className="btn-icon" aria-hidden="true">⬇️</span>
                Download PDF
              </a>
            )}
            <button
              onClick={onReset}
              className="btn btn-secondary btn-large"
              id="optimize-another-button"
            >
              <span className="btn-icon" aria-hidden="true">🔄</span>
              Optimize Another
            </button>
          </div>
        </article>
      </section>
    </div>
  )
}

export default ScoreDashboard
