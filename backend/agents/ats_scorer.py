"""ATS Scorer Agent — scores resume against job description requirements."""
from backend.llm.base import LLMProvider
from backend.models import ATSScore, JDAnalysis


ATS_SCORING_SYSTEM_PROMPT = """You are an expert ATS (Applicant Tracking System) Scorer.
Your role is to evaluate how well a resume matches a job description.

You MUST return valid JSON with the following schema:
{
  "overall_score": number (0-100),
  "skills_match_pct": number (0-100),
  "keyword_match_pct": number (0-100),
  "experience_relevance_pct": number (0-100),
  "missing_skills": ["string"],
  "missing_keywords": ["string"],
  "matched_skills": ["string"],
  "matched_keywords": ["string"],
  "breakdown": {
    "skills": {"score": number, "details": "string"},
    "keywords": {"score": number, "details": "string"},
    "experience": {"score": number, "details": "string"},
    "formatting": {"score": number, "details": "string"}
  }
}

Scoring Methodology:
- skills_match_pct: % of required skills found in resume
- keyword_match_pct: % of important ATS keywords found in resume
- experience_relevance_pct: How well experience descriptions match job requirements
- overall_score: Weighted average (skills 35%, keywords 30%, experience 25%, formatting 10%)
- Be honest and precise — don't inflate scores
- List ALL missing skills and keywords"""


async def score_resume(
    llm: LLMProvider,
    resume_text: str,
    jd_analysis: JDAnalysis,
) -> ATSScore:
    """Score a resume against extracted JD requirements.

    Args:
        llm: The LLM provider to use.
        resume_text: The full resume text content.
        jd_analysis: Structured JD analysis from the JD Analyzer agent.

    Returns:
        ATSScore with overall score, breakdowns, and missing items.
    """
    prompt = f"""Score the following resume against the job requirements.

JOB REQUIREMENTS:
- Title: {jd_analysis.job_title}
- Company: {jd_analysis.company}
- Required Skills: {', '.join(jd_analysis.required_skills)}
- Preferred Skills: {', '.join(jd_analysis.preferred_skills)}
- Keywords: {', '.join(jd_analysis.keywords)}
- Experience: {jd_analysis.experience_years}+ years
- Tech Stack: {', '.join(jd_analysis.tech_stack)}
- Responsibilities: {chr(10).join('  - ' + r for r in jd_analysis.responsibilities)}

RESUME:
---
{resume_text}
---

Analyze the resume thoroughly. Check each required skill, keyword, and responsibility.
Calculate match percentages precisely. List all missing items.
Return structured JSON with the ATS score breakdown."""

    result = await llm.generate(
        prompt=prompt,
        system=ATS_SCORING_SYSTEM_PROMPT,
        response_format="json",
    )

    return ATSScore(**result)
