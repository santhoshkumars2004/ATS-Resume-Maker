import { useEffect, useRef, useState } from 'react'

function JDInput({ onOptimize, onUploadTemplate, onUploadTemplateText, loading, health }) {
  const [jobDescription, setJobDescription] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [templateUploaded, setTemplateUploaded] = useState(false)
  const [uploadStatus, setUploadStatus] = useState('')
  const [inputMode, setInputMode] = useState('file')
  const [latexText, setLatexText] = useState('')
  const [selectedProvider, setSelectedProvider] = useState('')
  const [selectedModel, setSelectedModel] = useState('')
  const fileInputRef = useRef(null)
  const providerOptions = health?.available_providers || []
  const activeProvider = providerOptions.find((option) => option.id === selectedProvider)
  const supportedModels = activeProvider?.supported_models || []
  const selectedModelIsPreset = supportedModels.some((option) => option.value === selectedModel)
  const modelSelectValue = selectedModelIsPreset ? selectedModel : (activeProvider?.supports_custom_model ? '__custom__' : (selectedModel || ''))

  useEffect(() => {
    if (!providerOptions.length || selectedProvider) return

    const preferredProvider =
      providerOptions.find((option) => option.id === health?.default_provider && option.available)
      || providerOptions.find((option) => option.available)
      || providerOptions[0]

    setSelectedProvider(preferredProvider.id)
    setSelectedModel(preferredProvider.supports_model_override ? (preferredProvider.default_model || '') : '')
  }, [health?.default_provider, providerOptions, selectedProvider])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (jobDescription.trim().length < 50) return
    if (!companyName.trim()) return
    onOptimize(jobDescription, companyName, selectedProvider, selectedModel)
  }

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploadStatus('Uploading...')
    try {
      const result = await onUploadTemplate(file)
      setTemplateUploaded(true)
      setUploadStatus(`✅ ${result.message || `${file.name} uploaded successfully`}`)
    } catch (err) {
      setUploadStatus(`❌ ${err.message || 'Upload failed'}`)
    }
  }

  const handleTextUpload = async () => {
    if (!latexText.trim()) return
    setUploadStatus('Saving template...')
    try {
      if (onUploadTemplateText) {
        const result = await onUploadTemplateText(latexText)
        setTemplateUploaded(true)
        setUploadStatus(`✅ ${result.message || 'LaTeX template saved successfully'}`)
      }
    } catch (err) {
      setUploadStatus(`❌ ${err.message || 'Upload failed'}`)
    }
  }

  const canSubmit = jobDescription.trim().length >= 50 && companyName.trim() && !loading
  const canSaveText = Boolean(latexText.trim())

  const handleProviderChange = (e) => {
    const nextProviderId = e.target.value
    const nextProvider = providerOptions.find((option) => option.id === nextProviderId)

    setSelectedProvider(nextProviderId)
    setSelectedModel(nextProvider?.supports_model_override ? (nextProvider.default_model || '') : '')
  }

  const handleModelSelectChange = (e) => {
    const nextValue = e.target.value
    if (nextValue === '__custom__') {
      setSelectedModel('')
      return
    }

    setSelectedModel(nextValue)
  }

  return (
    <section className="jd-input-section">
      <form onSubmit={handleSubmit}>
        {/* Model Provider */}
        <div className="form-group">
          <label htmlFor="provider-select" className="form-label">
            🤖 AI Backend
          </label>
          <select
            id="provider-select"
            className="form-input"
            value={selectedProvider}
            onChange={handleProviderChange}
            disabled={!providerOptions.length || loading}
          >
            {providerOptions.map((option) => (
              <option key={option.id} value={option.id} disabled={!option.available}>
                {option.label}{option.available ? '' : ' (unavailable)'}
              </option>
            ))}
          </select>
          {health?.status !== 'healthy' && health?.connection_error && (
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 'var(--space-2)' }}>
              Backend is disconnected. You can still choose a provider, but save and optimize will work only after FastAPI reconnects.
            </p>
          )}
          {activeProvider?.reason && !activeProvider.available && (
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--danger)', marginTop: 'var(--space-2)' }}>
              {activeProvider.reason}
            </p>
          )}
        </div>

        {activeProvider?.supports_model_override && (
          <div className="form-group">
            <label htmlFor="model-name" className="form-label">
              🧠 Model
            </label>
            {supportedModels.length > 0 ? (
              <select
                id="model-name"
                className="form-input"
                value={modelSelectValue}
                onChange={handleModelSelectChange}
                disabled={loading}
              >
                {supportedModels.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
                {activeProvider?.supports_custom_model && (
                  <option value="__custom__">Custom model</option>
                )}
              </select>
            ) : (
              <input
                id="model-name"
                type="text"
                className="form-input"
                placeholder={activeProvider.default_model || 'Leave blank to use the default model'}
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
              />
            )}
            {activeProvider?.supports_custom_model && modelSelectValue === '__custom__' && (
              <input
                type="text"
                className="form-input"
                style={{ marginTop: 'var(--space-2)' }}
                placeholder="Enter your Ollama model name"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
              />
            )}
            {selectedProvider === 'codex' && (
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 'var(--space-2)' }}>
                Codex is now the default backend. If your login rejects a selected model, the backend will fall back to <code>gpt-5-codex</code>.
              </p>
            )}
            {selectedProvider === 'copilot' && (
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 'var(--space-2)' }}>
                Copilot model selection is sent as a best-effort CLI flag. If your local CLI ignores it, Copilot will use its own local default.
              </p>
            )}
          </div>
        )}

        {/* Company Name */}
        <div className="form-group">
          <label htmlFor="company-name" className="form-label">
            🏢 Company Name
          </label>
          <input
            id="company-name"
            type="text"
            className="form-input"
            placeholder="e.g., Google, Microsoft, Stripe..."
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            required
          />
        </div>

        {/* Job Description */}
        <div className="form-group">
          <label htmlFor="job-description" className="form-label">
            📋 Job Description
          </label>
          <textarea
            id="job-description"
            className="form-textarea"
            placeholder="Paste the full job description here...&#10;&#10;Include requirements, responsibilities, qualifications, tech stack — the more detail, the better the optimization."
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            rows={12}
            required
            minLength={50}
          />
          <p style={{
            fontSize: 'var(--text-xs)',
            color: jobDescription.length < 50 ? 'var(--text-muted)' : 'var(--success)',
            marginTop: 'var(--space-2)',
            fontFamily: 'var(--font-mono)',
          }}>
            {jobDescription.length} characters {jobDescription.length < 50 ? '(minimum 50)' : '✓'}
          </p>
        </div>

        {/* Template Upload */}
        <div className="form-group">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-2)' }}>
            <label className="form-label" style={{ marginBottom: 0 }}>📄 Your Resume Template</label>
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <button 
                type="button" 
                onClick={() => setInputMode('file')}
                style={{ fontSize: 'var(--text-xs)', padding: '2px 8px', borderRadius: '4px', background: inputMode === 'file' ? 'var(--bg-elevated)' : 'transparent', border: '1px solid var(--border-color)', color: inputMode === 'file' ? 'var(--text-primary)' : 'var(--text-muted)', cursor: 'pointer' }}
              >
                File Upload
              </button>
              <button 
                type="button" 
                onClick={() => setInputMode('paste')}
                style={{ fontSize: 'var(--text-xs)', padding: '2px 8px', borderRadius: '4px', background: inputMode === 'paste' ? 'var(--bg-elevated)' : 'transparent', border: '1px solid var(--border-color)', color: inputMode === 'paste' ? 'var(--text-primary)' : 'var(--text-muted)', cursor: 'pointer' }}
              >
                Paste LaTeX
              </button>
            </div>
          </div>

          {health?.template_loaded && !templateUploaded && (
            <div style={{ marginBottom: 'var(--space-4)', padding: 'var(--space-3)', background: 'rgba(99, 102, 241, 0.1)', border: '1px solid var(--accent-light)', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ fontSize: 'var(--text-sm)', color: 'var(--accent-light)', fontWeight: 'bold' }}>✓ Template loaded on server</span>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', margin: 0, marginTop: '2px' }}>Resume is loaded. You can click optimize!</p>
              </div>
              <button
                type="button"
                onClick={() => setTemplateUploaded(true)}
                className="btn btn-secondary"
                style={{ padding: '4px 12px', fontSize: 'var(--text-xs)' }}
              >
                Use Last Used LaTeX
              </button>
            </div>
          )}

          {inputMode === 'file' ? (
            <>
              <div
                className={`upload-zone ${templateUploaded ? 'active' : ''}`}
                onClick={() => fileInputRef.current?.click()}
                role="button"
                tabIndex={0}
                aria-label="Upload resume PDF or LaTeX template"
                onKeyDown={(e) => { if (e.key === 'Enter') fileInputRef.current?.click() }}
              >
                <div className="upload-icon" aria-hidden="true">
                  {templateUploaded ? '✅' : '📎'}
                </div>
                <p className="upload-text">
                  {uploadStatus || (
                    <>Click to upload your resume (<strong>.pdf</strong> or <strong>.tex</strong>)</>
                  )}
                </p>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 'var(--space-2)' }}>
                  Your resume will be analyzed and optimized for the job description
                </p>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.tex"
                onChange={handleFileChange}
                style={{ display: 'none' }}
                aria-hidden="true"
              />
            </>
          ) : (
            <div className="paste-zone">
              <textarea
                className="form-textarea"
                placeholder="% Paste your complete LaTeX (.tex) code here...&#10;% Don't forget %%BEGIN_SUMMARY%% tags!"
                value={latexText}
                onChange={(e) => {
                  setLatexText(e.target.value)
                }}
                rows={8}
                style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', marginBottom: 'var(--space-2)' }}
              />
              <button
                type="button"
                className="btn btn-secondary"
                style={{ width: '100%' }}
                onClick={handleTextUpload}
                disabled={!canSaveText}
              >
                {templateUploaded ? 'Update Text Template' : 'Save Text Template'}
              </button>
              {uploadStatus && inputMode === 'paste' && (
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--accent-light)', marginTop: 'var(--space-2)', textAlign: 'center' }}>
                  {uploadStatus}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Submit Button */}
        <div style={{ textAlign: 'center', marginTop: 'var(--space-8)' }}>
          <button
            type="submit"
            className="btn btn-primary btn-large"
            disabled={!canSubmit}
            id="optimize-button"
          >
            <span className="btn-icon" aria-hidden="true">⚡</span>
            Optimize Resume
          </button>
        </div>
      </form>
    </section>
  )
}

export default JDInput
