import { useEffect, useMemo, useState } from 'react'
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

function RoadmapActionTypeBadge({ action }) {
  const palette = action.action_type === 'safe_generated'
    ? { color: 'var(--success)', background: 'var(--success-bg)', border: 'rgba(52, 211, 153, 0.2)', label: 'Safe' }
    : action.action_type === 'phrase_tuning'
    ? { color: 'var(--warning)', background: 'var(--warning-bg)', border: 'rgba(251, 191, 36, 0.2)', label: 'Phrase' }
    : { color: 'var(--danger)', background: 'var(--danger-bg)', border: 'rgba(248, 113, 113, 0.2)', label: action.proof_required ? 'Needs proof' : 'Manual' }

  return (
    <span
      style={{
        fontSize: 'var(--text-xs)',
        fontWeight: 700,
        color: palette.color,
        background: palette.background,
        border: `1px solid ${palette.border}`,
        borderRadius: '999px',
        padding: '4px 10px',
        whiteSpace: 'nowrap',
      }}
    >
      {palette.label}
    </span>
  )
}

function RoadmapList({ title, subtitle, actions, emptyMessage, reviewMode = false, selectedSkills = [], onAddSkill }) {
  return (
    <div
      style={{
        padding: 'var(--space-5)',
        borderRadius: 'var(--radius-lg)',
        background: 'var(--bg-glass)',
        border: '1px solid var(--border-subtle)',
      }}
    >
      <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 700, marginBottom: 'var(--space-2)' }}>{title}</h3>
      <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>{subtitle}</p>
      {actions?.length ? (
        <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
          {actions.map((action, index) => (
            <article
              key={`${action.title}-${index}`}
              style={{
                padding: 'var(--space-4)',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-glass-strong)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center', marginBottom: 'var(--space-2)' }}>
                <strong style={{ fontSize: 'var(--text-sm)', flex: 1 }}>{action.title}</strong>
                <RoadmapActionTypeBadge action={action} />
                <span style={{ color: 'var(--success)', fontWeight: 700, fontSize: 'var(--text-sm)' }}>+{action.estimated_points}</span>
              </div>
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', margin: 0 }}>{action.detail}</p>
              {reviewMode && action.term && (
                <div style={{ marginTop: 'var(--space-3)', display: 'flex', justifyContent: 'flex-end' }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ padding: '8px 14px', fontSize: 'var(--text-sm)' }}
                    onClick={() => onAddSkill?.(action.term)}
                  >
                    {selectedSkills.includes(action.term) ? 'Added' : `Add ${action.term}`}
                  </button>
                </div>
              )}
            </article>
          ))}
        </div>
      ) : (
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', margin: 0 }}>{emptyMessage}</p>
      )}
    </div>
  )
}

function createInitialSelection(optimization) {
  return {
    apply_summary: Boolean(optimization?.summary_rewrite),
    apply_skills: Boolean((optimization?.skills_to_add?.length || 0) || (optimization?.skills_to_reorder?.length || 0)),
    approved_skills_to_add: [...(optimization?.skills_to_add || [])],
    approved_experience_indices: (optimization?.experience_rewrites || []).map((_, index) => index),
  }
}

function ScoreDashboard({ results, onReset, onApplySelectedChanges, applyingChanges, apiBase, authToken }) {
  const { jd_analysis, original_score, optimized_score, optimization, score_roadmap, pdf_filename, pdf_url, status, message, review_applied } = results
  const improvement = optimized_score.overall_score - original_score.overall_score
  const reviewMode = !review_applied
  const [selection, setSelection] = useState(() => createInitialSelection(optimization))
  const [downloadState, setDownloadState] = useState({ loading: false, error: '' })

  useEffect(() => {
    setSelection(createInitialSelection(optimization))
  }, [optimization, review_applied])

  const selectedChangeCount = useMemo(() => {
    let count = 0
    if (selection.apply_summary && optimization.summary_rewrite) count += 1
    if (selection.apply_skills) {
      count += 1
      count += selection.approved_skills_to_add.length
    }
    count += selection.approved_experience_indices.length
    return count
  }, [selection, optimization])

  const toggleExperience = (index) => {
    setSelection((current) => {
      const exists = current.approved_experience_indices.includes(index)
      return {
        ...current,
        approved_experience_indices: exists
          ? current.approved_experience_indices.filter((value) => value !== index)
          : [...current.approved_experience_indices, index].sort((a, b) => a - b),
      }
    })
  }

  const toggleSkill = (skill) => {
    setSelection((current) => {
      const exists = current.approved_skills_to_add.includes(skill)
      return {
        ...current,
        approved_skills_to_add: exists
          ? current.approved_skills_to_add.filter((value) => value !== skill)
          : [...current.approved_skills_to_add, skill],
      }
    })
  }

  const applyAllContentChanges = () => {
    setSelection((current) => ({
      ...current,
      apply_summary: Boolean(optimization?.summary_rewrite),
      approved_experience_indices: (optimization?.experience_rewrites || []).map((_, index) => index),
    }))
  }

  const clearContentChanges = () => {
    setSelection((current) => ({
      ...current,
      apply_summary: false,
      approved_experience_indices: [],
    }))
  }

  const applyAllSkillChanges = () => {
    setSelection((current) => ({
      ...current,
      apply_skills: Boolean((optimization?.skills_to_add?.length || 0) || (optimization?.skills_to_reorder?.length || 0)),
      approved_skills_to_add: [...(optimization?.skills_to_add || [])],
    }))
  }

  const clearSkillChanges = () => {
    setSelection((current) => ({
      ...current,
      apply_skills: false,
      approved_skills_to_add: [],
    }))
  }

  const handleQueueRoadmapSkill = (skill) => {
    setSelection((current) => {
      if (current.approved_skills_to_add.includes(skill)) {
        return current
      }

      return {
        ...current,
        apply_skills: true,
        approved_skills_to_add: [...current.approved_skills_to_add, skill],
      }
    })
  }

  const handleDownload = async () => {
    if (!pdf_filename || !pdf_url || !authToken) return

    setDownloadState({ loading: true, error: '' })

    try {
      const res = await fetch(`${apiBase}${pdf_url}`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `Download failed with status ${res.status}`)
      }

      const blob = await res.blob()
      const objectUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = pdf_filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(objectUrl)
      setDownloadState({ loading: false, error: '' })
    } catch (err) {
      setDownloadState({
        loading: false,
        error: err instanceof Error ? err.message : 'Download failed',
      })
    }
  }

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
          <h2 className="score-title">{reviewMode ? 'Projected Score' : 'Final Score'}</h2>
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

      {/* ATS Roadmap */}
      <section className="glass-card" style={{ padding: 'var(--space-6)', marginBottom: 'var(--space-8)' }} aria-label="ATS target roadmap">
        <header className="section-header">
          <h2 className="section-title">
            <span aria-hidden="true">🧭</span> ATS Target Roadmap
          </h2>
          <p className="section-subtitle">
            Current match rate, safe projected score, and the remaining changes needed to push toward 90+ or 100.
          </p>
        </header>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--space-4)', marginBottom: 'var(--space-6)' }}>
          <div style={{ padding: 'var(--space-4)', borderRadius: 'var(--radius-lg)', background: 'var(--bg-glass)', border: '1px solid var(--border-subtle)' }}>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--space-2)' }}>
              Current Match
            </p>
            <strong style={{ fontSize: 'var(--text-2xl)' }}>{score_roadmap?.current_score ?? original_score.overall_score}/100</strong>
          </div>
          <div style={{ padding: 'var(--space-4)', borderRadius: 'var(--radius-lg)', background: 'var(--bg-glass)', border: '1px solid var(--border-subtle)' }}>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--space-2)' }}>
              Safe Projected
            </p>
            <strong style={{ fontSize: 'var(--text-2xl)', color: 'var(--warning)' }}>{score_roadmap?.projected_score ?? optimized_score.overall_score}/100</strong>
          </div>
          <div style={{ padding: 'var(--space-4)', borderRadius: 'var(--radius-lg)', background: 'var(--bg-glass)', border: '1px solid var(--border-subtle)' }}>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--space-2)' }}>
              Likely Ceiling
            </p>
            <strong style={{ fontSize: 'var(--text-2xl)', color: 'var(--success)' }}>{score_roadmap?.likely_max_score ?? optimized_score.overall_score}/100</strong>
          </div>
        </div>

        {score_roadmap?.projected_score < 80 && (
          <div
            style={{
              marginBottom: 'var(--space-6)',
              padding: 'var(--space-4)',
              borderRadius: 'var(--radius-lg)',
              background: 'var(--warning-bg)',
              border: '1px solid rgba(251, 191, 36, 0.2)',
            }}
          >
            <p style={{ margin: 0, color: 'var(--warning)', fontWeight: 700 }}>
              The generated changes improve ATS coverage, but this JD still has real gaps. The roadmap below shows which extra verified requirements are blocking a 90+ score.
            </p>
          </div>
        )}

        {score_roadmap?.likely_max_score < 90 && (
          <div
            style={{
              marginBottom: 'var(--space-6)',
              padding: 'var(--space-4)',
              borderRadius: 'var(--radius-lg)',
              background: 'var(--danger-bg)',
              border: '1px solid rgba(248, 113, 113, 0.2)',
            }}
          >
            <p style={{ margin: 0, color: 'var(--danger)', fontWeight: 700 }}>
              Based on the remaining JD gaps, this resume is not modeled to reach 90+ without adding new truthful evidence or user-confirmed skills.
            </p>
          </div>
        )}

        <div style={{ marginBottom: 'var(--space-6)' }}>
          <RoadmapList
            title="Safe ATS Pass Path"
            subtitle="These are the truthful changes the tool already generated from your resume and RAG context."
            actions={score_roadmap?.safe_actions || []}
            emptyMessage="The optimizer did not generate any safe ATS changes for this run."
            reviewMode={reviewMode}
            selectedSkills={selection.approved_skills_to_add}
            onAddSkill={handleQueueRoadmapSkill}
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--space-6)' }}>
          <RoadmapList
            title={`To Reach 90+ (${score_roadmap?.gap_to_90 || 0} pts gap)`}
            subtitle="Apply the safe changes above, then focus on these next highest-impact requirements."
            actions={score_roadmap?.target_90_actions || []}
            emptyMessage="This run is already at or above 90, so no extra roadmap is needed for that threshold."
            reviewMode={reviewMode}
            selectedSkills={selection.approved_skills_to_add}
            onAddSkill={handleQueueRoadmapSkill}
          />
          <RoadmapList
            title={`To Reach 100 (${score_roadmap?.gap_to_100 || 0} pts gap)`}
            subtitle="This is the stretch plan. Use it to see which exact must-haves still keep the resume from a perfect scanner match."
            actions={score_roadmap?.target_100_actions || []}
            emptyMessage="There are no remaining modeled actions beyond the current projection."
            reviewMode={reviewMode}
            selectedSkills={selection.approved_skills_to_add}
            onAddSkill={handleQueueRoadmapSkill}
          />
        </div>

        {score_roadmap?.blockers?.length > 0 && (
          <div style={{ marginTop: 'var(--space-6)' }}>
            <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Hard Blockers For A Perfect Match
            </p>
            <div className="tag-list">
              {score_roadmap.blockers.map((blocker, index) => (
                <span key={`${blocker}-${index}`} className="tag tag-missing">{blocker}</span>
              ))}
            </div>
          </div>
        )}
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
      <DiffView
        optimization={optimization}
        originalScore={original_score}
        reviewMode={reviewMode}
        selection={selection}
        onApplyAllContent={applyAllContentChanges}
        onClearContent={clearContentChanges}
        onApplyAllSkills={applyAllSkillChanges}
        onClearSkills={clearSkillChanges}
        onToggleSummary={() => setSelection((current) => ({ ...current, apply_summary: !current.apply_summary }))}
        onToggleSkills={() => setSelection((current) => ({ ...current, apply_skills: !current.apply_skills }))}
        onToggleSkill={toggleSkill}
        onToggleExperience={toggleExperience}
        applyingChanges={applyingChanges}
      />

      {/* Download / Actions */}
      <section className="download-section" aria-label="Download optimized resume">
        <article className="glass-card download-card">
          <div className="download-icon" aria-hidden="true">
            {reviewMode ? '✅' : (pdf_filename ? '📄' : '📝')}
          </div>
          <h2 className="download-title">
            {reviewMode ? 'Review Your Changes' : (pdf_filename ? 'Your Optimized Resume is Ready!' : 'Resume Modified')}
          </h2>
          <p className="download-subtitle">
            {reviewMode
              ? `Select the summary, bullet rewrites, and skill additions you trust, then generate the final resume from only those approved changes. ${selectedChangeCount} items currently selected.`
              : pdf_filename
              ? `Score improved from ${original_score.overall_score} → ${optimized_score.overall_score} (+${improvement} points)`
              : (message || 'The modified .tex file has been saved. You can compile it manually.')
            }
          </p>

          <div style={{ display: 'flex', gap: 'var(--space-4)', justifyContent: 'center', flexWrap: 'wrap' }}>
            {reviewMode ? (
              <button
                onClick={() => onApplySelectedChanges(selection)}
                className="btn btn-primary btn-large"
                id="apply-selected-changes-button"
                disabled={applyingChanges || selectedChangeCount === 0}
              >
                <span className="btn-icon" aria-hidden="true">✅</span>
                {applyingChanges ? 'Applying Changes...' : 'Apply Selected Changes'}
              </button>
            ) : pdf_filename && (
              <button
                type="button"
                onClick={handleDownload}
                className="btn btn-primary btn-large"
                id="download-pdf-button"
                disabled={downloadState.loading}
              >
                <span className="btn-icon" aria-hidden="true">⬇️</span>
                {downloadState.loading ? 'Preparing Download...' : 'Download PDF'}
              </button>
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

          {!reviewMode && downloadState.error && (
            <p style={{ marginTop: 'var(--space-3)', color: 'var(--danger)', fontSize: 'var(--text-sm)' }}>
              {downloadState.error}
            </p>
          )}
        </article>
      </section>
    </div>
  )
}

export default ScoreDashboard
