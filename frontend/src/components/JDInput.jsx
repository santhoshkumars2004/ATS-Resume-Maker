import { useState, useRef } from 'react'

function JDInput({ onOptimize, onUploadTemplate, loading }) {
  const [jobDescription, setJobDescription] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [templateUploaded, setTemplateUploaded] = useState(false)
  const [uploadStatus, setUploadStatus] = useState('')
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
          <label className="form-label">📄 Upload Your Resume</label>
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
