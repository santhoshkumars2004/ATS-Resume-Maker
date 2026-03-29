"""JD Analyzer Agent — extracts structured requirements from job descriptions."""
from __future__ import annotations

import re

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
  "experience_years": integer,
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
- experience_years: The minimum years of experience mentioned as a whole number (0 if not specified)
- responsibilities: Key job responsibilities and duties"""

SECTION_BREAK_PATTERN = re.compile(r"^[A-Z][A-Za-z/&,\-() ]{2,40}:?\s*$")
VALUE_LABEL_PATTERN = re.compile(r"^\s*([A-Za-z][A-Za-z/&,\- ]{2,40})\s*:\s*(.+?)\s*$")

KNOWN_TECH_TERMS = {
    "python": "Python",
    "java": "Java",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "react.js": "React.js",
    "react": "React.js",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "express": "Express",
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "sql": "SQL",
    "nosql": "NoSQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "snowflake": "Snowflake",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "lambda": "AWS Lambda",
    "ec2": "AWS EC2",
    "s3": "AWS S3",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "terraform": "Terraform",
    "grafana": "Grafana",
    "prometheus": "Prometheus",
    "datadog": "Datadog",
    "splunk": "Splunk",
    "linux": "Linux",
    "shell": "Shell",
    "bash": "Shell",
    "tcp/ip": "TCP/IP",
    "dns": "DNS",
    "http/https": "HTTP/HTTPS",
    "oop": "OOP",
    "object oriented programming": "Object-Oriented Programming",
    "object-oriented programming": "Object-Oriented Programming",
    "rest api": "REST API",
    "restful api": "REST API",
    "restful apis": "REST API",
    "graphql": "GraphQL",
    "git": "Git",
    "github": "GitHub",
    "ci/cd": "CI/CD",
    "generative ai": "Generative AI",
    "ai/ml": "AI/ML",
    "machine learning": "Machine Learning",
    "forecasting": "Forecasting",
    "anomaly detection": "Anomaly Detection",
    "langchain": "LangChain",
    "llm": "LLM",
    "rag": "RAG",
    "telemetry": "Telemetry",
    "data pipelines": "Data Pipelines",
    "monitoring": "Monitoring",
    "observability": "Observability",
    "incident management": "Incident Management",
    "sre": "SRE",
    "site reliability engineering": "Site Reliability Engineering",
    "microservices": "Microservices",
}

ACTION_KEYWORDS = {
    "develop": "Develop",
    "maintain": "Maintain",
    "build": "Build",
    "implement": "Implement",
    "support": "Support",
    "assist": "Assist",
    "debug": "Debug",
    "troubleshoot": "Troubleshoot",
    "collaborate": "Collaborate",
    "document": "Document",
    "optimize": "Optimize",
    "design": "Design",
    "test": "Test",
    "deploy": "Deploy",
    "monitor": "Monitor",
    "analyze": "Analyze",
}

REQUIRED_SECTION_HINTS = (
    "skills required",
    "technical skills",
    "programming / technical skills",
    "programming/technical skills",
    "requirements",
)
PREFERRED_SECTION_HINTS = ("preferred", "bonus", "nice to have")
RESPONSIBILITY_SECTION_HINTS = ("major tasks", "responsibilities", "what you will do", "role responsibilities")


def _normalize(text: str) -> str:
    return " ".join(text.strip().split())


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        clean = _normalize(item)
        key = clean.casefold()
        if not clean or key in seen:
            continue
        seen.add(key)
        ordered.append(clean)
    return ordered


def _lines(job_description: str) -> list[str]:
    return [_normalize(line) for line in job_description.splitlines() if _normalize(line)]


def _extract_label_value(job_description: str, label: str) -> str:
    pattern = re.compile(rf"{re.escape(label)}\s*:\s*(.+)", re.IGNORECASE)
    match = pattern.search(job_description)
    return _normalize(match.group(1)) if match else ""


def _extract_experience_years(job_description: str) -> int:
    patterns = (
        r"(?:minimum\s+year\s+of\s+experience|experience)\s*:\s*(\d+)\s*[-–]\s*(\d+)",
        r"(\d+)\s*[-–]\s*(\d+)\s+years?",
        r"minimum\s+(\d+)\s+years?",
        r"(\d+)\+\s*years?",
    )
    for pattern in patterns:
        match = re.search(pattern, job_description, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0


def _extract_section_lines(job_description: str, section_hints: tuple[str, ...]) -> list[str]:
    raw_lines = job_description.splitlines()
    collected: list[str] = []
    capture = False

    for raw_line in raw_lines:
        line = _normalize(raw_line)
        if not line:
            if capture:
                break
            continue

        normalized_line = line.casefold().rstrip(":")
        if normalized_line in section_hints:
            capture = True
            continue

        if capture and SECTION_BREAK_PATTERN.match(line):
            break

        if capture:
            if VALUE_LABEL_PATTERN.match(line):
                _, value = VALUE_LABEL_PATTERN.match(line).groups()
                collected.append(value)
            else:
                collected.append(line.lstrip("-•"))

    return [_normalize(line) for line in collected if _normalize(line)]


def _is_atomic_term(value: str) -> bool:
    clean = _normalize(value).strip(" ,.;:-")
    if not clean:
        return False

    lowered = clean.casefold()
    if lowered in KNOWN_TECH_TERMS:
        return True

    if re.search(r"[./+#]", clean):
        return True

    if re.fullmatch(r"[A-Z]{2,8}", clean):
        return True

    if len(clean.split()) <= 4 and any(char.isupper() for char in clean):
        return True

    return False


def _split_compound_terms(value: str) -> list[str]:
    clean = _normalize(value)
    if not clean:
        return []

    results: list[str] = []
    parenthetical_chunks = re.findall(r"\(([^)]*)\)", clean)
    head = re.sub(r"\([^)]*\)", "", clean).strip(" ,.;:-")

    if head and len(head.split()) <= 4 and not re.search(r"\s+(?:and|or)\s+", head, flags=re.IGNORECASE):
        results.append(head)

    chunks = parenthetical_chunks or [clean]
    for chunk in chunks:
        pieces = re.split(r"\s/\s|,|;|\|", chunk)
        if len(pieces) == 1 and re.search(r"\s+(?:and|or)\s+", chunk, flags=re.IGNORECASE):
            candidate_pieces = re.split(r"\s+(?:and|or)\s+", chunk, flags=re.IGNORECASE)
            if all(_is_atomic_term(piece) or piece.casefold() in KNOWN_TECH_TERMS for piece in candidate_pieces):
                pieces = candidate_pieces

        for piece in pieces:
            item = _normalize(piece).strip(" ,.;:-")
            if item:
                results.append(item)

    return _unique(results)


def _canonical_term(term: str) -> str:
    clean = _normalize(term).strip(" ,.;:-")
    if not clean:
        return ""

    lowered = clean.casefold()
    if lowered in KNOWN_TECH_TERMS:
        return KNOWN_TECH_TERMS[lowered]

    if re.fullmatch(r"[A-Z]{2,8}", clean):
        return clean

    if re.search(r"\.js$", clean, flags=re.IGNORECASE):
        base = clean[:-3].strip()
        return f"{base.title()}.js"

    if re.search(r"[./+#]", clean):
        return clean.upper() if len(clean) <= 8 else clean

    words = clean.split()
    if len(words) <= 4 and any(char.isupper() for char in clean):
        return clean

    if len(words) <= 3:
        return " ".join(word.capitalize() if word.islower() else word for word in words)

    return clean


def _extract_known_terms(job_description: str) -> list[str]:
    searchable = f" {_normalize(job_description).casefold()} "
    found: list[str] = []
    for raw_term, canonical in KNOWN_TECH_TERMS.items():
        pattern = re.compile(rf"(?<![a-z0-9]){re.escape(raw_term)}(?![a-z0-9])", re.IGNORECASE)
        if pattern.search(searchable):
            found.append(canonical)
    return _unique(found)


def _extract_requirement_terms(job_description: str) -> tuple[list[str], list[str]]:
    required_lines = _extract_section_lines(job_description, REQUIRED_SECTION_HINTS)
    preferred_lines = _extract_section_lines(job_description, PREFERRED_SECTION_HINTS)

    required_terms: list[str] = []
    preferred_terms: list[str] = []

    for line in required_lines:
        required_terms.extend(_extract_terms_from_line(line))
    for line in preferred_lines:
        preferred_terms.extend(_extract_terms_from_line(line))

    return (
        _unique([_canonical_term(term) for term in required_terms if _canonical_term(term)]),
        _unique([_canonical_term(term) for term in preferred_terms if _canonical_term(term)]),
    )


def _extract_responsibilities(job_description: str) -> list[str]:
    section_lines = _extract_section_lines(job_description, RESPONSIBILITY_SECTION_HINTS)
    if section_lines:
        return _unique(section_lines[:10])

    lines = _lines(job_description)
    inferred: list[str] = []
    for line in lines:
        lowered = line.casefold()
        if any(lowered.startswith(verb) for verb in ACTION_KEYWORDS):
            inferred.append(line)
    return _unique(inferred[:10])


def _extract_keywords(job_description: str, responsibilities: list[str], tech_terms: list[str]) -> list[str]:
    keywords = list(tech_terms)
    for responsibility in responsibilities:
        lowered = responsibility.casefold()
        for verb, keyword in ACTION_KEYWORDS.items():
            if verb in lowered:
                keywords.append(keyword)
    return _unique(keywords)


def _extract_terms_from_line(line: str) -> list[str]:
    normalized = _normalize(line)
    if not normalized:
        return []

    extracted = _extract_known_terms(normalized)
    if extracted:
        return extracted

    if (
        len(normalized.split()) <= 8
        or re.search(r"[(/,;|)]", normalized)
        or re.search(r"\s+(?:and|or)\s+", normalized, flags=re.IGNORECASE)
    ):
        return [_canonical_term(term) for term in _split_compound_terms(normalized) if _canonical_term(term)]

    return []


def _merge_ordered(primary: list[str], secondary: list[str]) -> list[str]:
    return _unique([*primary, *secondary])


def _hybridize_jd_analysis(result: dict, job_description: str, company_name: str) -> JDAnalysis:
    llm_analysis = JDAnalysis(**result)

    required_terms, preferred_terms = _extract_requirement_terms(job_description)
    tech_terms = _extract_known_terms(job_description)
    responsibilities = _extract_responsibilities(job_description)
    keywords = _extract_keywords(job_description, responsibilities, tech_terms)

    job_title = llm_analysis.job_title or _extract_label_value(job_description, "Job Title")
    education = llm_analysis.education or _extract_label_value(job_description, "Qualification")
    job_type = llm_analysis.job_type or _extract_label_value(job_description, "Job Type")
    location = llm_analysis.location or _extract_label_value(job_description, "Location") or "India" if "india" in job_description.casefold() else ""
    experience_years = llm_analysis.experience_years or _extract_experience_years(job_description)

    merged_required = _merge_ordered(llm_analysis.required_skills, required_terms)
    merged_preferred = _merge_ordered(llm_analysis.preferred_skills, preferred_terms)
    merged_tech_stack = _merge_ordered(llm_analysis.tech_stack, tech_terms)
    merged_keywords = _merge_ordered(llm_analysis.keywords, keywords + merged_required + merged_tech_stack)
    merged_responsibilities = _merge_ordered(llm_analysis.responsibilities, responsibilities)

    return JDAnalysis(
        job_title=job_title,
        company=company_name,
        required_skills=merged_required,
        preferred_skills=merged_preferred,
        keywords=merged_keywords,
        experience_years=experience_years,
        tech_stack=merged_tech_stack,
        responsibilities=merged_responsibilities,
        education=education,
        job_type=job_type,
        location=location,
    )


async def analyze_jd(llm: LLMProvider, job_description: str, company_name: str) -> JDAnalysis:
    """Analyze a job description and extract structured requirements."""
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

    result["company"] = company_name
    return _hybridize_jd_analysis(result, job_description, company_name)
