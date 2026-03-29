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
  - Prefer atomic, reusable skill names such as "AWS", "Azure", "GCP", "Grafana", "Prometheus", "Datadog"
  - If the JD uses grouped phrasing like "AWS / Azure / GCP" or "Grafana / Prometheus / Datadog", return separate items instead of one long phrase
  - Never return category labels or grouped section lines such as "Languages: Python, Java" or "Tools & Platforms: Git, AWS"
- skills_to_reorder: Full reordered skills list with most relevant to JD first
  - Keep the skills section compact and realistic for a one-page resume when possible
  - Prefer hard skills and technical tools only
  - Do NOT include soft skills like communication, interpersonal skills, quick learning, or problem solving in the technical skills section
  - Avoid duplicates and avoid long paragraph-like lists
  - Never include job titles, verbs, or generic phrases like "software development", "collaboration", "develop", or "maintain"
- experience_rewrites: Reword bullets to naturally include missing keywords + action verbs
  - Keep the factual content the same, just optimize wording
  - Use strong action verbs: Architected, Implemented, Optimized, Led, Designed
  - Quantify achievements where possible (metrics, percentages, scale)
  - The "original" field must EXACTLY match text in the resume
- summary_rewrite: Tailored professional summary highlighting JD-relevant experience
  - Keep it concise, ideally 2 sentences and freshers-friendly
- keywords_to_inject: Important ATS keywords that should appear in the resume
  - Prefer concise 1-4 word ATS terms instead of sentence fragments
  - Split grouped requirements into separate keywords when possible
  - Keep non-technical action verbs and generic phrases out of the technical skills section; those belong in summary/bullets only
- Do NOT fabricate experience — only reword and emphasize existing experience
- Optimize for generic ATS matching across any job description, not just human readability
- Prioritize exact JD wording for required skills, mandatory tools, and repeated phrases when the resume already supports them
- If a required skill is not supported by the resume or RAG context, do NOT invent it. Leave it missing so the user can decide manually.
- Prefer edits that improve shortlist odds:
  - mirror exact required terms naturally
  - strengthen the most relevant experience bullets first
  - keep the resume tight enough for early-career candidates to stay near one page
  - avoid stuffing too many weak or generic keywords into one section
- Target a 90+ ATS match rate whenever the resume truthfully supports it
- If the current ATS score is below 80, do NOT be conservative:
  - use the summary rewrite aggressively
  - use enough bullet rewrites to close the biggest requirement gaps
  - move all strongly supported JD skills into the skills section
  - prefer a fuller, higher-coverage optimization over a tiny diff
- When building skills_to_reorder:
  - preserve a compact categorized layout
  - prefer concrete technologies over broad phrases
  - place the highest-priority JD skills early
- When building experience_rewrites:
  - cover the biggest missing required skills and keywords first
  - use only evidence already present in the resume or RAG context
  - rewrite as many bullets as needed to materially improve ATS coverage, up to 8 strong rewrites
- Every major resume-supported missing requirement should appear in at least one of:
  - skills_to_add
  - skills_to_reorder
  - summary_rewrite
  - experience_rewrites
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
include missing keywords naturally. Add only resume-supported missing skills.
Rewrite the summary using the strongest JD-aligned evidence. Prefer the exact
required JD terms when they are truthfully supported by the resume or RAG context.
Keep the final resume concise and avoid turning the skills section into a paragraph.
Aim for the strongest truthful ATS coverage possible, with a practical target of 90+.
Return structured JSON with all edits."""

    result = await llm.generate(
        prompt=prompt,
        system=OPTIMIZER_SYSTEM_PROMPT,
        response_format="json",
    )

    return ResumeOptimization(**result)
