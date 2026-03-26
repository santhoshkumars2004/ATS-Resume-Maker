function LoadingOverlay({ step }) {
  const steps = [
    { label: 'Analyzing job description...', icon: '🔍' },
    { label: 'Scoring your resume...', icon: '📊' },
    { label: 'Retrieving relevant experience...', icon: '🧠' },
    { label: 'Generating optimizations...', icon: '✨' },
    { label: 'Compiling tailored resume...', icon: '📄' },
  ]

  return (
    <div className="loading-overlay" role="status" aria-live="polite">
      <div className="loading-content">
        <div className="loading-spinner" aria-hidden="true" />
        <p className="loading-text">Optimizing your resume</p>
        <p className="loading-subtext">Running multi-agent pipeline...</p>

        <ul className="loading-steps">
          {steps.map((s, i) => (
            <li
              key={i}
              className={`loading-step ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}
            >
              <span aria-hidden="true">{i < step ? '✅' : s.icon}</span>
              {s.label}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default LoadingOverlay
