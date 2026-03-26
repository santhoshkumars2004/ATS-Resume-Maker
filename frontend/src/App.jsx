import { useState, useCallback } from 'react'
import JDInput from './components/JDInput'
import ScoreDashboard from './components/ScoreDashboard'
import LoadingOverlay from './components/LoadingOverlay'
import './index.css'

const API_BASE = 'http://localhost:8000'

function App() {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingStep, setLoadingStep] = useState(0)
  const [error, setError] = useState(null)
  const [health, setHealth] = useState(null)

  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/health`)
      const data = await res.json()
      setHealth(data)
    } catch {
      setHealth({ status: 'error', llm_provider: 'unknown' })
    }
  }, [])

  // Check health on mount
  useState(() => { checkHealth() })

  const handleOptimize = async (jobDescription, companyName) => {
    setLoading(true)
    setLoadingStep(0)
    setError(null)
    setResults(null)

    try {
      // Simulate step progression
      const stepTimer = setInterval(() => {
        setLoadingStep(prev => Math.min(prev + 1, 4))
      }, 1500)

      const res = await fetch(`${API_BASE}/api/optimize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_description: jobDescription,
          company_name: companyName,
        }),
      })

      clearInterval(stepTimer)

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || `Server error: ${res.status}`)
      }

      const data = await res.json()
      setLoadingStep(5)

      // Small delay for the final step animation
      setTimeout(() => {
        setResults(data)
        setLoading(false)
      }, 500)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  const handleUploadTemplate = async (file) => {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch(`${API_BASE}/api/upload-template`, {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Upload failed')
      return data
    } catch (err) {
      setError(err.message)
      throw err
    }
  }

  const handleReset = () => {
    setResults(null)
    setError(null)
  }

  return (
    <>
      {loading && <LoadingOverlay step={loadingStep} />}

      <main className="app-container">
        <header className="app-header">
          <div className="app-logo">
            <div className="app-logo-icon" aria-hidden="true">⚡</div>
            <h1 className="app-title">Resume ATS Optimizer</h1>
          </div>
          <p className="app-subtitle">
            Paste a job description, get an ATS score, and auto-generate a tailored resume — all in one click
          </p>
        </header>

        {health && (
          <nav className="status-bar" aria-label="System status">
            <span className="status-chip">
              <span className={`status-dot ${health.status === 'healthy' ? '' : 'error'}`} />
              {health.status === 'healthy' ? 'Connected' : 'Disconnected'}
            </span>
            <span className="status-chip">
              🤖 LLM: {health.llm_provider || 'unknown'}
            </span>
            <span className="status-chip">
              <span className={`status-dot ${health.template_loaded ? '' : 'warning'}`} />
              Template: {health.template_loaded ? 'Loaded' : 'Not uploaded'}
            </span>
            <span className="status-chip">
              <span className={`status-dot ${health.tectonic_available ? '' : 'warning'}`} />
              LaTeX: {health.tectonic_available ? 'Ready' : 'Not installed'}
            </span>
          </nav>
        )}

        {error && (
          <div className="glass-card" style={{ padding: 'var(--space-4)', marginBottom: 'var(--space-6)', borderColor: 'var(--danger)' }}>
            <p style={{ color: 'var(--danger)', fontWeight: 600 }}>⚠️ {error}</p>
          </div>
        )}

        {!results ? (
          <JDInput
            onOptimize={handleOptimize}
            onUploadTemplate={handleUploadTemplate}
            loading={loading}
          />
        ) : (
          <ScoreDashboard
            results={results}
            onReset={handleReset}
            apiBase={API_BASE}
          />
        )}
      </main>
    </>
  )
}

export default App
