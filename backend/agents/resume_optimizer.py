"""Resume Optimizer Agent — generates structured LaTeX-compatible edits."""
from backend.llm.base import LLMProvider
from backend.models import ATSScore, JDAnalysis, ResumeOptimization


OPTIMIZER_SYSTEM_PROMPT = """You are an expert Resume Optimizer specializing in ATS optimization.
Your role is to suggest specific, actionable edits to improve a resume's ATS score.

You MUST return valid JSON with the following schema:
{
  "skills_to_add": ["string"],
  "skills_to_reorder": ["string"],
  "experience_rewrites": [
    {
      "section": "string",
      "original": "string (exact original bullet text)",
      "replacement": "string (improved bullet text)"
    }
  ],
  "summary_rewrite": "string",
  "keywords_to_inject": ["string"]
}

Guidelines:
- skills_to_add: Only add skills the candidate actually has (from their experience)
- skills_to_reorder: Full reordered skills list with most relevant to JD first
- experience_rewrites: Reword bullets to naturally include missing keywords + action verbs
  - Keep the factual content the same, just optimize wording
  - Use strong action verbs: Architected, Implemented, Optimized, Led, Designed
  - Quantify achievements where possible (metrics, percentages, scale)
  - The "original" field must EXACTLY match text in the resume
- summary_rewrite: Tailored professional summary highlighting JD-relevant experience
- keywords_to_inject: Important ATS keywords that should appear in the resume
- Do NOT fabricate experience — only reword and emphasize existing experience
- Ensure all text is plain text compatible with LaTeX (no special chars without escaping)"""


async def optimize_resume(
    llm: LLMProvider,
    resume_text: str,
    jd_analysis: JDAnalysis,
    ats_score: ATSScore,
    rag_context: str = "",
) -> ResumeOptimization:
    """Generate optimization suggestions for the resume.

    Args:
        llm: The LLM provider to use.
        resume_text: The full resume text content.
        jd_analysis: Structured JD analysis.
        ats_score: Current ATS score to improve.
        rag_context: Additional relevant experience from RAG.

    Returns:
        ResumeOptimization with specific structured edits.
    """
    rag_section = ""
    if rag_context:
        rag_section = f"""
ADDITIONAL RELEVANT EXPERIENCE (from knowledge base):
---
{rag_context}
---
Use this to enrich the resume with relevant project experience."""

    prompt = f"""Optimize the following resume to improve its ATS score for this job.

CURRENT ATS SCORE: {ats_score.overall_score}/100
MISSING SKILLS: {', '.join(ats_score.missing_skills)}
MISSING KEYWORDS: {', '.join(ats_score.missing_keywords)}

JOB REQUIREMENTS:
- Title: {jd_analysis.job_title}
- Required Skills: {', '.join(jd_analysis.required_skills)}
- Keywords: {', '.join(jd_analysis.keywords)}
- Tech Stack: {', '.join(jd_analysis.tech_stack)}

CURRENT RESUME:
---
{resume_text}
---
{rag_section}
Generate specific edits to improve the ATS score. Reword experience bullets to
include missing keywords naturally. Add missing skills. Rewrite the summary.
Return structured JSON with all edits."""

    result = await llm.generate(
        prompt=prompt,
        system=OPTIMIZER_SYSTEM_PROMPT,
        response_format="json",
    )

    return ResumeOptimization(**result)
