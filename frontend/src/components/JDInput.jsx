import { useState, useRef } from 'react'

function JDInput({ onOptimize, onUploadTemplate, onUploadTemplateText, loading, health }) {
  const [jobDescription, setJobDescription] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [templateUploaded, setTemplateUploaded] = useState(false)
  const [uploadStatus, setUploadStatus] = useState('')
  const [inputMode, setInputMode] = useState('file')
  const [latexText, setLatexText] = useState('')
  const fileInputRef = useRef(null)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (jobDescription.trim().length < 50) return
    if (!companyName.trim()) return
    onOptimize(jobDescription, companyName)
  }

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploadStatus('Uploading...')
    try {
      await onUploadTemplate(file)
      setTemplateUploaded(true)
      setUploadStatus(`✅ ${file.name} uploaded successfully`)
    } catch {
      setUploadStatus('❌ Upload failed')
    }
  }

  const handleTextUpload = async () => {
    if (!latexText.trim()) return
    setUploadStatus('Saving template...')
    try {
      if (onUploadTemplateText) {
        await onUploadTemplateText(latexText)
        setTemplateUploaded(true)
        setUploadStatus('✅ LaTeX template saved successfully')
      }
    } catch {
      setUploadStatus('❌ Upload failed')
    }
  }

  const canSubmit = jobDescription.trim().length >= 50 && companyName.trim() && !loading

  return (
    <section className="jd-input-section">
      <form onSubmit={handleSubmit}>
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
                onChange={(e) => setLatexText(e.target.value)}
                rows={8}
                style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', marginBottom: 'var(--space-2)' }}
              />
              <button
                type="button"
                className="btn btn-secondary"
                style={{ width: '100%' }}
                onClick={handleTextUpload}
                disabled={!latexText.trim() || templateUploaded}
              >
                {templateUploaded ? '✅ Saved successfully' : 'Save Text Template'}
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
