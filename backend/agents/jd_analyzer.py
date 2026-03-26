"""JD Analyzer Agent — extracts structured requirements from job descriptions."""
from backend.llm.base import LLMProvider
from backend.models import JDAnalysis


JD_ANALYSIS_SYSTEM_PROMPT = """You are an expert Job Description Analyzer for ATS optimization.
Your role is to parse job descriptions and extract structured information.

You MUST return valid JSON with the following schema:
{
  "job_title": "string",
  "company": "string",
  "required_skills": ["string"],
  "preferred_skills": ["string"],
  "keywords": ["string"],
  "experience_years": number,
  "tech_stack": ["string"],
  "responsibilities": ["string"],
  "education": "string",
  "job_type": "string",
  "location": "string"
}

Guidelines:
- required_skills: Skills explicitly listed as required or mandatory
- preferred_skills: Skills listed as "nice to have", "preferred", or "bonus"
- keywords: Important terms/phrases that ATS systems scan for (action verbs, industry terms)
- tech_stack: All technologies mentioned (languages, frameworks, tools, platforms)
- experience_years: The minimum years of experience mentioned (0 if not specified)
- responsibilities: Key job responsibilities and duties"""


async def analyze_jd(llm: LLMProvider, job_description: str, company_name: str) -> JDAnalysis:
    """Analyze a job description and extract structured requirements.

    Args:
        llm: The LLM provider to use.
        job_description: Raw job description text.
        company_name: Name of the target company.

    Returns:
        JDAnalysis with extracted requirements.
    """
    prompt = f"""Analyze the following job description from {company_name} and extract all relevant information.

JOB DESCRIPTION:
---
{job_description}
---

Extract: job title, required skills, preferred skills, ATS keywords, years of experience,
tech stack, responsibilities, education requirements, job type, and location.
Return as structured JSON."""

    result = await llm.generate(
        prompt=prompt,
        system=JD_ANALYSIS_SYSTEM_PROMPT,
        response_format="json",
    )

    # Override company name with user-provided value
    result["company"] = company_name

    return JDAnalysis(**result)
