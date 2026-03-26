"""Pydantic models for API request/response schemas."""
from pydantic import BaseModel, Field


# ── Request Models ──────────────────────────────────────────────

class OptimizeRequest(BaseModel):
    """Request body for the /api/optimize endpoint."""
    job_description: str = Field(..., min_length=50, description="Full job description text")
    company_name: str = Field(..., min_length=1, description="Target company name")


# ── JD Analysis ─────────────────────────────────────────────────

class JDAnalysis(BaseModel):
    """Structured output from the JD Analyzer agent."""
    job_title: str = ""
    company: str = ""
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    keywords: list[str] = []
    experience_years: int = 0
    tech_stack: list[str] = []
    responsibilities: list[str] = []
    education: str = ""
    job_type: str = ""
    location: str = ""


# ── ATS Score ───────────────────────────────────────────────────

class ScoreBreakdownItem(BaseModel):
    """Individual category score with details."""
    score: int = 0
    details: str = ""


class ScoreBreakdown(BaseModel):
    """Detailed score breakdown by category."""
    skills: ScoreBreakdownItem = ScoreBreakdownItem()
    keywords: ScoreBreakdownItem = ScoreBreakdownItem()
    experience: ScoreBreakdownItem = ScoreBreakdownItem()
    formatting: ScoreBreakdownItem = ScoreBreakdownItem()


class ATSScore(BaseModel):
    """ATS scoring result."""
    overall_score: int = 0
    skills_match_pct: int = 0
    keyword_match_pct: int = 0
    experience_relevance_pct: int = 0
    missing_skills: list[str] = []
    missing_keywords: list[str] = []
    matched_skills: list[str] = []
    matched_keywords: list[str] = []
    breakdown: ScoreBreakdown = ScoreBreakdown()


# ── Resume Optimization ────────────────────────────────────────

class ExperienceRewrite(BaseModel):
    """A single experience bullet rewrite."""
    section: str = ""
    original: str = ""
    replacement: str = ""


class ResumeOptimization(BaseModel):
    """Structured edits to apply to the resume."""
    skills_to_add: list[str] = []
    skills_to_reorder: list[str] = []
    experience_rewrites: list[ExperienceRewrite] = []
    summary_rewrite: str = ""
    keywords_to_inject: list[str] = []


# ── API Response ────────────────────────────────────────────────

class OptimizeResponse(BaseModel):
    """Full response from the /api/optimize endpoint."""
    jd_analysis: JDAnalysis
    original_score: ATSScore
    optimization: ResumeOptimization
    optimized_score: ATSScore
    pdf_filename: str = ""
    pdf_url: str = ""
    status: str = "success"
    message: str = ""
