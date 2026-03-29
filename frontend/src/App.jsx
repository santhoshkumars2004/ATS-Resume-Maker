import { useEffect, useState } from 'react'
import AuthScreen from './components/AuthScreen'
import HistoryPanel from './components/HistoryPanel'
import JDInput from './components/JDInput'
import LoadingOverlay from './components/LoadingOverlay'
import ScoreDashboard from './components/ScoreDashboard'
import './index.css'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
const TOKEN_STORAGE_KEY = 'resume_ats_auth_token'
const USER_STORAGE_KEY = 'resume_ats_auth_user'

const FALLBACK_PROVIDER_OPTIONS = [
  {
    id: 'codex',
    label: 'Codex CLI',
    available: true,
    supports_model_override: true,
    default_model: 'gpt-5.4',
    supported_models: [
      { value: 'gpt-5.4', label: 'GPT-5.4' },
      { value: 'gpt-5.4-mini', label: 'GPT-5.4-Mini' },
      { value: 'gpt-5.3-codex', label: 'GPT-5.3-Codex' },
      { value: 'gpt-5.3-codex-spark-preview', label: 'GPT-5.3-Codex-Spark-Preview' },
      { value: 'gpt-5.2-codex', label: 'GPT-5.2-Codex' },
      { value: 'gpt-5.2', label: 'GPT-5.2' },
      { value: 'gpt-5.1-codex-max', label: 'GPT-5.1-Codex-Max' },
      { value: 'gpt-5.1-codex-mini', label: 'GPT-5.1-Codex-Mini' },
    ],
    reason: null,
  },
  {
    id: 'copilot',
    label: 'GitHub Copilot CLI',
    available: true,
    supports_model_override: true,
    default_model: 'gpt-4.1',
    supported_models: [
      { value: 'gpt-4.1', label: 'GPT-4.1' },
      { value: 'gpt-4o', label: 'GPT-4o' },
      { value: 'gpt-5-mini', label: 'GPT-5 mini' },
      { value: 'claude-haiku-4.5', label: 'Claude Haiku 4.5' },
      { value: 'claude-opus-4.5', label: 'Claude Opus 4.5' },
      { value: 'claude-opus-4.6', label: 'Claude Opus 4.6' },
      { value: 'claude-sonnet-4', label: 'Claude Sonnet 4' },
      { value: 'claude-sonnet-4.5', label: 'Claude Sonnet 4.5' },
      { value: 'claude-sonnet-4.6', label: 'Claude Sonnet 4.6' },
      { value: 'gemini-3-flash-preview', label: 'Gemini 3 Flash (Preview)' },
      { value: 'gpt-5.1-codex', label: 'GPT-5.1-Codex' },
      { value: 'gpt-5.1-codex-mini', label: 'GPT-5.1-Codex-Mini (Preview)' },
      { value: 'gpt-5.2', label: 'GPT-5.2' },
      { value: 'gpt-5.2-codex', label: 'GPT-5.2-Codex' },
      { value: 'gpt-5.3-codex', label: 'GPT-5.3-Codex' },
      { value: 'gpt-5.4', label: 'GPT-5.4' },
    ],
    reason: null,
  },
  {
    id: 'llama',
    label: 'Llama via Ollama',
    available: true,
    supports_model_override: true,
    default_model: 'llama3',
    supported_models: [
      { value: 'llama3', label: 'llama3' },
      { value: 'llama3.1', label: 'llama3.1' },
      { value: 'llama3.2', label: 'llama3.2' },
      { value: 'llama3.3', label: 'llama3.3' },
      { value: 'qwen2.5-coder', label: 'qwen2.5-coder' },
      { value: 'mistral', label: 'mistral' },
      { value: 'deepseek-r1', label: 'deepseek-r1' },
    ],
    supports_custom_model: true,
    reason: null,
  },
]

function describeRequestError(err) {
  if (err instanceof TypeError) {
    return `Cannot reach backend at ${API_BASE}. Start FastAPI on that port or set VITE_API_BASE_URL.`
  }

  if (err instanceof Error && err.message) {
    return err.message
  }

  return 'Request failed'
}

function readStoredUser() {
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function buildHeaders(token, extraHeaders = {}) {
  const headers = new Headers(extraHeaders)
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  return headers
}

async function readJson(response) {
  return response.json().catch(() => ({}))
}

function App() {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingStep, setLoadingStep] = useState(0)
  const [applyingChanges, setApplyingChanges] = useState(false)
  const [error, setError] = useState(null)
  const [health, setHealth] = useState(null)
  const [authReady, setAuthReady] = useState(false)
  const [authLoading, setAuthLoading] = useState(false)
  const [authError, setAuthError] = useState(null)
  const [authToken, setAuthToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY) || '')
  const [authUser, setAuthUser] = useState(() => readStoredUser())
  const [historyItems, setHistoryItems] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [activeHistoryId, setActiveHistoryId] = useState(null)
  const [deletingHistoryId, setDeletingHistoryId] = useState(null)

  const persistSession = (token, user) => {
    setAuthToken(token)
    setAuthUser(user)
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user))
  }

  const clearSession = () => {
    setAuthToken('')
    setAuthUser(null)
    setResults(null)
    setHistoryItems([])
    setActiveHistoryId(null)
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    localStorage.removeItem(USER_STORAGE_KEY)
  }

  const checkHealth = async (token = authToken) => {
    try {
      const res = await fetch(`${API_BASE}/api/health`, {
        headers: buildHeaders(token),
      })
      if (!res.ok) {
        throw new Error(`Health check failed with status ${res.status}`)
      }

      const data = await res.json()
      setHealth(data)
    } catch (err) {
      setHealth({
        status: 'error',
        llm_provider: 'unknown',
        default_provider: 'codex',
        available_providers: FALLBACK_PROVIDER_OPTIONS,
        connection_error: describeRequestError(err),
        template_loaded: false,
        tectonic_available: false,
        authenticated: false,
        current_user: null,
      })
    }
  }

  const authenticatedFetch = async (path, options = {}, token = authToken) => {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: buildHeaders(token, options.headers || {}),
    })

    if (res.status === 401) {
      clearSession()
      await checkHealth('')
      throw new Error('Your session expired. Please sign in again.')
    }

    return res
  }

  const loadHistory = async (token = authToken) => {
    if (!token) {
      setHistoryItems([])
      return
    }

    setHistoryLoading(true)
    try {
      const res = await authenticatedFetch('/api/history', {}, token)
      const data = await readJson(res)
      if (!res.ok) {
        throw new Error(data.detail || `History request failed with status ${res.status}`)
      }
      setHistoryItems(data.items || [])
    } catch (err) {
      setError(describeRequestError(err))
    } finally {
      setHistoryLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false

    const bootstrap = async () => {
      const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY) || ''
      let sessionInvalid = false
      await checkHealth(storedToken)

      if (!storedToken) {
        if (!cancelled) {
          setAuthReady(true)
        }
        return
      }

      try {
        const res = await fetch(`${API_BASE}/api/auth/me`, {
          headers: buildHeaders(storedToken),
        })
        const data = await readJson(res)

        if (!res.ok) {
          sessionInvalid = res.status === 401
          throw new Error(data.detail || 'Session expired.')
        }

        if (cancelled) return

        setAuthToken(storedToken)
        setAuthUser(data)
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(data))
        await loadHistory(storedToken)
      } catch (err) {
        if (err instanceof TypeError) {
          if (!cancelled) {
            setAuthReady(true)
          }
          return
        }

        if (sessionInvalid) {
          clearSession()
          if (!cancelled) {
            setAuthError('Your previous session expired. Please sign in again.')
          }
          await checkHealth('')
        } else if (!cancelled) {
          setAuthError(describeRequestError(err))
        }
      } finally {
        if (!cancelled) {
          setAuthReady(true)
        }
      }
    }

    bootstrap()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (health?.status === 'healthy') return undefined

    const intervalId = setInterval(() => {
      checkHealth(authToken)
    }, 5000)

    return () => clearInterval(intervalId)
  }, [authToken, health?.status])

  const handleAuthenticate = async (mode, payload) => {
    setAuthLoading(true)
    setAuthError(null)
    setError(null)

    try {
      const endpoint = mode === 'register' ? '/api/auth/register' : '/api/auth/login'
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await readJson(res)

      if (!res.ok) {
        throw new Error(data.detail || `${mode === 'register' ? 'Registration' : 'Login'} failed`)
      }

      persistSession(data.token, data.user)
      setResults(null)
      setActiveHistoryId(null)
      await Promise.all([checkHealth(data.token), loadHistory(data.token)])
    } catch (err) {
      setAuthError(describeRequestError(err))
    } finally {
      setAuthReady(true)
      setAuthLoading(false)
    }
  }

  const handleLogout = async () => {
    setAuthLoading(true)
    setError(null)
    setAuthError(null)

    try {
      if (authToken) {
        await fetch(`${API_BASE}/api/auth/logout`, {
          method: 'POST',
          headers: buildHeaders(authToken),
        })
      }
    } finally {
      clearSession()
      await checkHealth('')
      setAuthLoading(false)
    }
  }

  const handleOptimize = async (jobDescription, companyName, provider, model) => {
    setLoading(true)
    setLoadingStep(0)
    setError(null)
    setResults(null)
    setActiveHistoryId(null)

    let stepTimer

    try {
      stepTimer = setInterval(() => {
        setLoadingStep((prev) => Math.min(prev + 1, 4))
      }, 1500)

      const payload = {
        job_description: jobDescription,
        company_name: companyName,
      }

      if (provider) {
        payload.provider = provider
      }
      if (model?.trim()) {
        payload.model = model.trim()
      }

      const res = await authenticatedFetch('/api/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await readJson(res)

      if (!res.ok) {
        throw new Error(data.detail || `Server error: ${res.status}`)
      }

      await loadHistory()
      setLoadingStep(5)

      setTimeout(() => {
        setResults(data)
        setLoading(false)
      }, 500)
    } catch (err) {
      setError(describeRequestError(err))
      setLoading(false)
    } finally {
      if (stepTimer) {
        clearInterval(stepTimer)
      }
    }
  }

  const handleUploadTemplate = async (file) => {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await authenticatedFetch('/api/upload-template', {
        method: 'POST',
        body: formData,
      })
      const data = await readJson(res)
      if (!res.ok) throw new Error(data.detail || 'Upload failed')
      await checkHealth()
      return data
    } catch (err) {
      const message = describeRequestError(err)
      setError(message)
      throw new Error(message)
    }
  }

  const handleUploadTemplateText = async (text) => {
    try {
      const res = await authenticatedFetch('/api/upload-template-text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: text }),
      })
      const data = await readJson(res)
      if (!res.ok) throw new Error(data.detail || 'Upload failed')
      await checkHealth()
      return data
    } catch (err) {
      const message = describeRequestError(err)
      setError(message)
      throw new Error(message)
    }
  }

  const handleApplySelectedChanges = async (selection) => {
    if (!results) return

    setApplyingChanges(true)
    setError(null)
    setActiveHistoryId(null)

    try {
      const payload = {
        company_name: results.jd_analysis.company || '',
        provider: results.provider || undefined,
        model: results.model?.trim() ? results.model : undefined,
        jd_analysis: results.jd_analysis,
        original_score: results.original_score,
        optimization: results.optimization,
        selection,
      }

      const res = await authenticatedFetch('/api/apply-selected-changes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await readJson(res)

      if (!res.ok) {
        throw new Error(data.detail || `Server error: ${res.status}`)
      }

      setResults(data)
      await loadHistory()
    } catch (err) {
      setError(describeRequestError(err))
    } finally {
      setApplyingChanges(false)
    }
  }

  const handleOpenHistory = async (entryId) => {
    setError(null)
    try {
      const res = await authenticatedFetch(`/api/history/${entryId}`)
      const data = await readJson(res)

      if (!res.ok) {
        throw new Error(data.detail || `History lookup failed with status ${res.status}`)
      }

      setResults(data.result)
      setActiveHistoryId(entryId)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (err) {
      setError(describeRequestError(err))
    }
  }

  const handleDeleteHistory = async (entryId) => {
    const item = historyItems.find((historyItem) => historyItem.id === entryId)
    const label = item?.review_applied ? 'saved run' : 'draft'
    if (!window.confirm(`Delete this ${label}? This will also remove its generated files.`)) {
      return
    }

    setDeletingHistoryId(entryId)
    setError(null)

    try {
      const res = await authenticatedFetch(`/api/history/${entryId}`, {
        method: 'DELETE',
      })
      const data = await readJson(res)
      if (!res.ok) {
        throw new Error(data.detail || `Delete failed with status ${res.status}`)
      }

      if (activeHistoryId === entryId) {
        setResults(null)
        setActiveHistoryId(null)
      }

      await loadHistory()
    } catch (err) {
      setError(describeRequestError(err))
    } finally {
      setDeletingHistoryId(null)
    }
  }

  const handleReset = () => {
    setResults(null)
    setError(null)
    setActiveHistoryId(null)
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
              🤖 LLM: {health.default_provider || health.llm_provider || 'unknown'}
            </span>
            <span className="status-chip">
              <span className={`status-dot ${health.template_loaded ? '' : 'warning'}`} />
              Template: {health.template_loaded ? 'Loaded' : 'Not uploaded'}
            </span>
            <span className="status-chip">
              <span className={`status-dot ${health.tectonic_available ? '' : 'warning'}`} />
              LaTeX: {health.tectonic_available ? 'Ready' : 'Not installed'}
            </span>
            <span className="status-chip">
              <span className={`status-dot ${authUser ? '' : 'warning'}`} />
              {authUser ? `Signed in as ${authUser.name}` : 'Sign in required'}
            </span>
          </nav>
        )}

        {error && (
          <div className="glass-card" style={{ padding: 'var(--space-4)', marginBottom: 'var(--space-6)', borderColor: 'var(--danger)' }}>
            <p style={{ color: 'var(--danger)', fontWeight: 600 }}>⚠️ {error}</p>
          </div>
        )}

        {!authReady ? (
          <section className="glass-card auth-card auth-card--loading">
            <p className="auth-loading-text">Checking your saved session and backend status...</p>
          </section>
        ) : !authUser ? (
          <AuthScreen
            onAuthenticate={handleAuthenticate}
            loading={authLoading}
            error={authError}
            backendConnected={health?.status === 'healthy'}
          />
        ) : (
          <>
            <section className="glass-card user-toolbar">
              <div>
                <p className="user-toolbar-label">Workspace</p>
                <h2 className="user-toolbar-title">{authUser.name}&rsquo;s saved resume workspace</h2>
                <p className="user-toolbar-subtitle">
                  Your template, optimized resumes, and approved review changes are stored under your account.
                </p>
              </div>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleLogout}
                disabled={authLoading}
              >
                {authLoading ? 'Signing out...' : 'Sign out'}
              </button>
            </section>

            <div className="workspace-shell">
              <section className="workspace-main">
                {!results ? (
                  <JDInput
                    onOptimize={handleOptimize}
                    onUploadTemplate={handleUploadTemplate}
                    onUploadTemplateText={handleUploadTemplateText}
                    loading={loading}
                    health={health}
                  />
                ) : (
                  <ScoreDashboard
                    results={results}
                    onReset={handleReset}
                    onApplySelectedChanges={handleApplySelectedChanges}
                    applyingChanges={applyingChanges}
                    apiBase={API_BASE}
                    authToken={authToken}
                  />
                )}
              </section>

              <aside className="workspace-sidebar">
                <HistoryPanel
                  items={historyItems}
                  loading={historyLoading}
                  activeId={activeHistoryId}
                  onOpen={handleOpenHistory}
                  onDelete={handleDeleteHistory}
                  deletingId={deletingHistoryId}
                />
              </aside>
            </div>
          </>
        )}
      </main>
    </>
  )
}

export default App
