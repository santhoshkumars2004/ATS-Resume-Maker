"""Mock LLM provider for development/testing without API keys."""
import json
from typing import Any

from .base import LLMProvider


# Realistic mock responses for each agent type
MOCK_JD_ANALYSIS = {
    "job_title": "Senior Software Engineer",
    "company": "TechCorp Inc.",
    "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "CI/CD"],
    "preferred_skills": ["React", "TypeScript", "GraphQL", "Redis", "AWS"],
    "keywords": [
        "microservices", "distributed systems", "REST API", "agile",
        "system design", "scalable", "cloud-native", "DevOps"
    ],
    "experience_years": 5,
    "tech_stack": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "AWS", "React"],
    "responsibilities": [
        "Design and develop scalable microservices",
        "Lead code reviews and mentor junior developers",
        "Collaborate with product and design teams",
        "Optimize API performance and database queries",
        "Implement CI/CD pipelines and DevOps practices"
    ],
    "education": "Bachelor's in Computer Science or equivalent",
    "job_type": "Full-time",
    "location": "Remote"
}

MOCK_ATS_SCORE = {
    "overall_score": 62,
    "skills_match_pct": 55,
    "keyword_match_pct": 48,
    "experience_relevance_pct": 78,
    "missing_skills": ["Kubernetes", "CI/CD", "Docker"],
    "missing_keywords": ["microservices", "distributed systems", "cloud-native", "DevOps"],
    "matched_skills": ["Python", "FastAPI", "PostgreSQL"],
    "matched_keywords": ["REST API", "agile", "scalable"],
    "breakdown": {
        "skills": {
            "score": 55,
            "details": "3 of 6 required skills matched. Missing: Kubernetes, CI/CD, Docker."
        },
        "keywords": {
            "score": 48,
            "details": "3 of 8 key terms found. Missing: microservices, distributed systems, cloud-native, DevOps."
        },
        "experience": {
            "score": 78,
            "details": "Work experience is relevant. Could better emphasize leadership and system design."
        },
        "formatting": {
            "score": 90,
            "details": "LaTeX formatting is ATS-friendly. Good use of sections and bullet points."
        }
    }
}

MOCK_OPTIMIZATION = {
    "skills_to_add": ["Kubernetes", "Docker", "CI/CD"],
    "skills_to_reorder": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "CI/CD", "React", "TypeScript"],
    "experience_rewrites": [
        {
            "section": "experience_0",
            "original": "Developed web applications using Python and various frameworks",
            "replacement": "Architected and developed scalable microservices using Python and FastAPI, serving 10K+ RPM in a cloud-native distributed system"
        },
        {
            "section": "experience_1",
            "original": "Worked with databases and optimized queries",
            "replacement": "Optimized PostgreSQL database performance, reducing query latency by 40% through indexing strategies and query restructuring"
        },
        {
            "section": "experience_2",
            "original": "Collaborated with team members on projects",
            "replacement": "Led code reviews and mentored 3 junior developers in agile sprints, driving DevOps best practices across the team"
        }
    ],
    "summary_rewrite": "Senior Software Engineer with 5+ years of experience designing scalable microservices and distributed systems. Expert in Python, FastAPI, and cloud-native architectures with Kubernetes and Docker. Passionate about DevOps practices, CI/CD pipelines, and building high-performance REST APIs.",
    "keywords_to_inject": ["microservices", "distributed systems", "cloud-native", "DevOps"]
}

MOCK_OPTIMIZED_SCORE = {
    "overall_score": 89,
    "skills_match_pct": 92,
    "keyword_match_pct": 85,
    "experience_relevance_pct": 91,
    "missing_skills": [],
    "missing_keywords": [],
    "matched_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "CI/CD"],
    "matched_keywords": [
        "microservices", "distributed systems", "REST API", "agile",
        "scalable", "cloud-native", "DevOps", "system design"
    ],
    "breakdown": {
        "skills": {"score": 92, "details": "All 6 required skills now matched."},
        "keywords": {"score": 85, "details": "All 8 key terms now present in resume."},
        "experience": {"score": 91, "details": "Experience bullets now strongly align with JD requirements."},
        "formatting": {"score": 90, "details": "LaTeX formatting remains ATS-friendly."}
    }
}


class MockProvider(LLMProvider):
    """Mock provider returning realistic sample responses for dev/testing."""

    def __init__(self):
        self._call_count = 0

    async def generate(
        self,
        prompt: str,
        system: str = "",
        response_format: str = "json",
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        self._call_count += 1
        prompt_lower = prompt.lower()
        system_lower = system.lower()

        # Route based on system prompt (most reliable) then prompt content
        if "ats" in system_lower and "scorer" in system_lower:
            # ATS Scorer — check if this is the second scoring call
            if self._call_count > 3:
                return MOCK_OPTIMIZED_SCORE
            return MOCK_ATS_SCORE
        elif "optimizer" in system_lower or "resume optimizer" in system_lower:
            return MOCK_OPTIMIZATION
        elif "job description" in system_lower and "analyzer" in system_lower:
            return MOCK_JD_ANALYSIS
        elif "score" in prompt_lower[:50]:
            # "Score the following" at the start of prompt
            if self._call_count > 3:
                return MOCK_OPTIMIZED_SCORE
            return MOCK_ATS_SCORE
        elif "optimiz" in prompt_lower[:50]:
            return MOCK_OPTIMIZATION
        else:
            # Default: use call order (pipeline runs: analyze → score → optimize → score)
            return MOCK_JD_ANALYSIS

    async def generate_text(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
    ) -> str:
        result = await self.generate(prompt, system, response_format="text", temperature=temperature)
        return json.dumps(result, indent=2)
