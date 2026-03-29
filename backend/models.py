"""Pydantic models for API request/response schemas."""
from pydantic import BaseModel, Field, field_validator


def _coerce_score_to_int(value):
    """Accept float-like model output and normalize it into an integer score."""
    if value is None or value == "":
        return 0

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, str):
        stripped = value.strip().rstrip("%")
        if not stripped:
            return 0
        value = stripped

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return value

    rounded = int(numeric + 0.5) if numeric >= 0 else int(numeric - 0.5)
    return max(0, min(100, rounded))


# ── Request Models ──────────────────────────────────────────────

class OptimizeRequest(BaseModel):
    """Request body for the /api/optimize endpoint."""
    job_description: str = Field(..., min_length=50, description="Full job description text")
    company_name: str = Field(..., min_length=1, description="Target company name")
    provider: str | None = Field(default=None, description="LLM provider override")
    model: str | None = Field(default=None, description="Optional model override")


class ReviewSelection(BaseModel):
    """User-approved subset of suggested changes."""
    apply_summary: bool = True
    apply_skills: bool = True
    approved_skills_to_add: list[str] = []
    approved_experience_indices: list[int] = []


class ApplyChangesRequest(BaseModel):
    """Request body for applying only reviewed changes."""
    company_name: str = Field(..., min_length=1, description="Target company name")
    provider: str | None = Field(default=None, description="LLM provider override")
    model: str | None = Field(default=None, description="Optional model override")
    jd_analysis: "JDAnalysis"
    original_score: "ATSScore"
    optimization: "ResumeOptimization"
    selection: ReviewSelection


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

    @field_validator("experience_years", mode="before")
    @classmethod
    def normalize_experience_years(cls, value):
        return _coerce_score_to_int(value)


# ── ATS Score ───────────────────────────────────────────────────

class ScoreBreakdownItem(BaseModel):
    """Individual category score with details."""
    score: int = 0
    details: str = ""

    @field_validator("score", mode="before")
    @classmethod
    def normalize_score(cls, value):
        return _coerce_score_to_int(value)


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

    @field_validator(
        "overall_score",
        "skills_match_pct",
        "keyword_match_pct",
        "experience_relevance_pct",
        mode="before",
    )
    @classmethod
    def normalize_numeric_scores(cls, value):
        return _coerce_score_to_int(value)


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


class ScoreRoadmapAction(BaseModel):
    """A concrete action that can increase ATS match rate."""
    title: str = ""
    detail: str = ""
    action_type: str = ""
    term: str = ""
    estimated_points: int = 0
    target_score: int = 0
    proof_required: bool = False
    required: bool = False


class ScoreRoadmap(BaseModel):
    """Roadmap from current score to safer ATS targets."""
    current_score: int = 0
    projected_score: int = 0
    likely_max_score: int = 0
    gap_to_90: int = 0
    gap_to_100: int = 0
    safe_actions: list[ScoreRoadmapAction] = []
    target_90_actions: list[ScoreRoadmapAction] = []
    target_100_actions: list[ScoreRoadmapAction] = []
    blockers: list[str] = []


# ── API Response ────────────────────────────────────────────────

class OptimizeResponse(BaseModel):
    """Full response from the /api/optimize endpoint."""
    jd_analysis: JDAnalysis
    original_score: ATSScore
    optimization: ResumeOptimization
    optimized_score: ATSScore
    score_roadmap: ScoreRoadmap = ScoreRoadmap()
    provider: str = ""
    model: str = ""
    pdf_filename: str = ""
    pdf_url: str = ""
    tex_path: str = ""
    pdf_path: str = ""
    log_path: str = ""
    output_dir: str = ""
    status: str = "success"
    message: str = ""
    review_applied: bool = False


ApplyChangesRequest.model_rebuild()
