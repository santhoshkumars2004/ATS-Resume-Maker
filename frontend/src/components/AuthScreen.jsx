import { useMemo, useState } from 'react'

const INITIAL_LOGIN = { email: '', password: '' }
const INITIAL_REGISTER = { name: '', email: '', password: '' }

function AuthScreen({ onAuthenticate, loading, error, backendConnected }) {
  const [mode, setMode] = useState('login')
  const [loginForm, setLoginForm] = useState(INITIAL_LOGIN)
  const [registerForm, setRegisterForm] = useState(INITIAL_REGISTER)

  const activeForm = useMemo(
    () => (mode === 'login' ? loginForm : registerForm),
    [loginForm, mode, registerForm],
  )

  const handleSubmit = async (event) => {
    event.preventDefault()
    await onAuthenticate(mode, activeForm)
  }

  return (
    <section className="auth-layout">
      <article className="glass-card auth-card auth-card--shell">
        <div className="auth-overview">
          <div className="auth-status-row">
            <span className={`auth-status-chip ${backendConnected ? 'online' : 'offline'}`}>
              <span className="auth-status-dot" aria-hidden="true" />
              {backendConnected ? 'Backend connected' : 'Backend offline'}
            </span>
            <span className="auth-status-chip">Private resume workspaces</span>
          </div>

          <div className="auth-card-header">
            <span className="auth-eyebrow">Self-hosted accounts</span>
            <h2 className="auth-title">{mode === 'login' ? 'Sign in to your workspace' : 'Create your account'}</h2>
            <p className="auth-subtitle">
              Each user gets their own template, saved optimization history, downloadable outputs, and approved change set.
            </p>
          </div>

          <div className="auth-hero-callout">
            <h3>Resume tuning with memory</h3>
            <p>
              Your last template, reviewed edits, and saved runs stay tied to your account, so the app feels like a real workspace instead of a one-time form.
            </p>
            <div className="auth-hero-points" aria-label="Workspace highlights">
              <span className="auth-hero-point">Private templates</span>
              <span className="auth-hero-point">Saved ATS history</span>
              <span className="auth-hero-point">Review-first workflow</span>
            </div>
          </div>

          <div className="auth-note-grid">
            <div className="auth-note-card">
              <h3>Saved templates</h3>
              <p>Users keep their own uploaded PDF or LaTeX template instead of sharing one global file.</p>
            </div>
            <div className="auth-note-card">
              <h3>Stored changes</h3>
              <p>Every optimize run and every reviewed version is saved so people can come back later.</p>
            </div>
            <div className="auth-note-card">
              <h3>Open-source ready</h3>
              <p>This works as a lightweight self-hosted account system without external auth setup.</p>
            </div>
          </div>
        </div>

        <div className="auth-form-panel">
          <div className="auth-form-header">
            <span className="auth-panel-eyebrow">{mode === 'login' ? 'Welcome back' : 'New account setup'}</span>
            <h3>{mode === 'login' ? 'Pick up from your last saved run' : 'Create a private workspace for your resume runs'}</h3>
            <p>
              {mode === 'login'
                ? 'Sign in to reopen saved drafts, final resumes, and your uploaded template.'
                : 'Your account keeps resume uploads, generated outputs, and reviewed changes organized under one profile.'}
            </p>
          </div>

          <div className="auth-tabs" role="tablist" aria-label="Authentication mode">
            <button
              type="button"
              className={`auth-tab ${mode === 'login' ? 'active' : ''}`}
              onClick={() => setMode('login')}
            >
              Sign in
            </button>
            <button
              type="button"
              className={`auth-tab ${mode === 'register' ? 'active' : ''}`}
              onClick={() => setMode('register')}
            >
              Create account
            </button>
          </div>

          {error && (
            <div className="auth-error">
              {error}
            </div>
          )}

          <form className="auth-form" onSubmit={handleSubmit}>
            {mode === 'register' && (
              <div className="form-group">
                <label htmlFor="register-name" className="form-label">
                  Name
                </label>
                <input
                  id="register-name"
                  className="form-input"
                  type="text"
                  value={registerForm.name}
                  onChange={(event) => setRegisterForm((current) => ({ ...current, name: event.target.value }))}
                  placeholder="Your name"
                  minLength={2}
                  required
                />
              </div>
            )}

            <div className="form-group">
              <label htmlFor={`${mode}-email`} className="form-label">
                Email
              </label>
              <input
                id={`${mode}-email`}
                className="form-input"
                type="email"
                value={activeForm.email}
                onChange={(event) => {
                  const value = event.target.value
                  if (mode === 'login') {
                    setLoginForm((current) => ({ ...current, email: value }))
                  } else {
                    setRegisterForm((current) => ({ ...current, email: value }))
                  }
                }}
                placeholder="you@example.com"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor={`${mode}-password`} className="form-label">
                Password
              </label>
              <input
                id={`${mode}-password`}
                className="form-input"
                type="password"
                value={activeForm.password}
                onChange={(event) => {
                  const value = event.target.value
                  if (mode === 'login') {
                    setLoginForm((current) => ({ ...current, password: value }))
                  } else {
                    setRegisterForm((current) => ({ ...current, password: value }))
                  }
                }}
                placeholder={mode === 'login' ? 'Enter your password' : 'At least 8 characters'}
                minLength={8}
                required
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-large auth-submit"
              disabled={loading || !backendConnected}
            >
              {loading
                ? (mode === 'login' ? 'Signing in...' : 'Creating account...')
                : (mode === 'login' ? 'Sign in' : 'Create account')
              }
            </button>
          </form>

          <div className="auth-panel-note">
            <strong>{backendConnected ? 'Ready to work' : 'Backend needed'}</strong>
            <p>
              {backendConnected
                ? 'Sign in and continue from your last saved optimization history.'
                : 'Start the FastAPI backend first, then sign in to use uploads, optimization, and history.'}
            </p>
          </div>
        </div>
      </article>
    </section>
  )
}

export default AuthScreen
