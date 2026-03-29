"""ATS scorer that uses a hybrid job-scanner style resume-to-JD benchmark."""
from __future__ import annotations

import re
from collections.abc import Iterable

from backend.llm.base import LLMProvider
from backend.models import ATSScore, JDAnalysis, ScoreBreakdown, ScoreBreakdownItem


COMMON_ALIASES = {
    "c++": ["cpp", "c plus plus"],
    "c#": ["c sharp"],
    "node.js": ["nodejs", "node js"],
    "react.js": ["reactjs", "react"],
    "next.js": ["nextjs", "next js"],
    "vue.js": ["vuejs", "vue"],
    "javascript": ["java script", "js"],
    "typescript": ["type script", "ts"],
    "html5": ["html"],
    "css3": ["css"],
    "rest api": ["rest apis", "restful api", "restful apis", "restful api development"],
    "oop": ["oops", "object oriented programming", "object-oriented programming"],
    "sql": ["postgresql", "mysql", "sqlite", "mssql", "relational database"],
    "nosql": ["no sql", "no-sql", "mongodb", "redis", "dynamodb", "chromadb", "cloud db"],
    "front-end": ["frontend", "front end", "ui development"],
    "aws": ["amazon web services", "lambda", "ec2", "s3"],
    "communication skills": ["communication", "strong communication"],
    "interpersonal skills": ["interpersonal", "interpersonal communication"],
    "problem solving": ["problem-solving", "problem solving skills"],
    "quick learning ability": ["quick learner", "quick learning", "quickly learn", "adaptable"],
    "performance optimization": ["performance tuning", "performance improvement", "optimized performance"],
    "defect fixing": ["bug fixing", "issue fixing", "debugging", "troubleshooting"],
    "logical design concepts": ["logical designing concepts", "logical and designing concepts", "logical & designing concepts"],
    "css frameworks": ["bootstrap", "foundation", "tailwind css", "tailwind"],
    "ai/ml": ["aiml", "machine learning", "ml", "artificial intelligence"],
    "generative ai": ["genai", "llm", "large language model", "large language models"],
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "the",
    "their",
    "to",
    "with",
    "using",
    "use",
    "should",
    "have",
    "has",
    "good",
    "strong",
    "basic",
    "basics",
    "knowledge",
    "required",
    "requirement",
    "skills",
    "skill",
    "concepts",
    "concept",
}

GENERIC_DESCRIPTOR_TOKENS = {
    "ability",
    "adaptive",
    "building",
    "collaboratively",
    "components",
    "dashboard",
    "dashboards",
    "deployment",
    "development",
    "environment",
    "evolving",
    "experience",
    "exposure",
    "fundamentals",
    "guidance",
    "implementation",
    "implementations",
    "implementing",
    "integrating",
    "integration",
    "maintainable",
    "maintenance",
    "player",
    "practical",
    "principles",
    "proof",
    "proofs",
    "scalable",
    "service",
    "services",
    "simple",
    "support",
    "team",
    "teamwork",
    "testing",
    "translate",
    "translating",
    "understanding",
    "use",
    "cases",
    "validation",
    "working",
}

EARLY_CAREER_MARKERS = {
    "intern",
    "internship",
    "trainee",
    "graduate",
    "student",
    "project",
    "projects",
    "fresher",
}


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _searchable_resume_text(value: str) -> str:
    text = value.replace("\\\\", " ")
    text = re.sub(r"\\[a-zA-Z*]+(?:\[[^\]]*\])?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    text = text.replace("&", " and ")
    return _normalize_space(text)


def _signature(value: str) -> str:
    normalized = _normalize_space(value)
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9+#]+", "", normalized)
    return normalized


def _content_tokens(value: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9+#]+", _normalize_space(value))
    return [token for token in tokens if token not in STOPWORDS and (len(token) > 2 or token in {"c", "c++", "c#"})]


def _primary_tokens(value: str) -> list[str]:
    primary = [token for token in _content_tokens(value) if token not in GENERIC_DESCRIPTOR_TOKENS]
    return primary or _content_tokens(value)


def _unique_terms(terms: Iterable[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for term in terms:
        cleaned = _normalize_space(term)
        if not cleaned:
            continue
        sig = _signature(cleaned)
        if not sig or sig in seen:
            continue
        seen.add(sig)
        ordered.append(term.strip())
    return ordered


def _term_variants(term: str) -> list[str]:
    base = _normalize_space(term)
    if not base:
        return []

    variants = {
        base,
        re.sub(r"\([^)]*\)", "", base).strip(),
        base.replace("&", "and"),
        base.replace(" and ", " & "),
        base.replace("-", " "),
        base.replace("-", ""),
        base.replace(".js", "js"),
        base.replace(".js", ""),
    }

    for alias in COMMON_ALIASES.get(base, []):
        variants.add(_normalize_space(alias))

    for key, aliases in COMMON_ALIASES.items():
        normalized_aliases = {_normalize_space(alias) for alias in aliases}
        if base == key or base in normalized_aliases:
            variants.add(key)
            variants.update(normalized_aliases)

    return [variant for variant in variants if variant]


def _variant_regex(variant: str) -> re.Pattern[str]:
    escaped = re.escape(variant)
    escaped = escaped.replace(r"\ ", r"\s+")
    escaped = escaped.replace(r"\-", r"[-\s]?")
    escaped = escaped.replace(r"\.", r"[.\s]?")
    escaped = escaped.replace(r"\/", r"(?:/|\s+)")
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])")


def _variant_match_score(variant: str, searchable_resume_text: str, resume_tokens: set[str]) -> float:
    if _variant_regex(variant).search(searchable_resume_text):
        return 1.0

    tokens = list(dict.fromkeys(_primary_tokens(variant)))
    if not tokens:
        return 0.0

    matched_tokens = [token for token in tokens if token in resume_tokens]
    if not matched_tokens:
        return 0.0

    ratio = len(matched_tokens) / len(tokens)
    score = 0.0
    if ratio >= 1.0:
        score = 0.92
    elif ratio >= 0.8:
        score = 0.80
    elif ratio >= 0.66:
        score = 0.70
    elif ratio >= 0.5:
        score = 0.58
    elif ratio >= 0.34:
        score = 0.42
    elif ratio >= 0.2:
        score = 0.26

    if tokens and tokens[0] in resume_tokens and len(tokens) > 1:
        score = max(score, 0.48)

    return min(1.0, score)


def _term_match_score(term: str, searchable_resume_text: str, resume_tokens: set[str]) -> float:
    best_score = 0.0
    for variant in _term_variants(term):
        best_score = max(best_score, _variant_match_score(variant, searchable_resume_text, resume_tokens))
        if best_score >= 1.0:
            return 1.0

    parts = [part.strip() for part in re.split(r"/|,| and | & |\(|\)", _normalize_space(term)) if part.strip()]
    if len(parts) > 1:
        part_scores = [
            _term_match_score(part, searchable_resume_text, resume_tokens)
            for part in parts
            if _primary_tokens(part)
        ]
        if part_scores:
            best_score = max(best_score, sum(part_scores) / len(part_scores))

    return min(1.0, best_score)


def _terms_equivalent(left: str, right: str) -> bool:
    left_sig = _signature(left)
    right_sig = _signature(right)
    if not left_sig or not right_sig:
        return False
    if left_sig == right_sig:
        return True
    if min(len(left_sig), len(right_sig)) >= 4 and (left_sig in right_sig or right_sig in left_sig):
        return True

    left_tokens = set(_primary_tokens(left))
    right_tokens = set(_primary_tokens(right))
    if not left_tokens or not right_tokens:
        return False

    overlap = len(left_tokens & right_tokens)
    return overlap >= max(1, min(len(left_tokens), len(right_tokens)))


def _term_weight(term: str, emphasis_pool: Iterable[str]) -> float:
    weight = 1.0
    if any(_terms_equivalent(term, candidate) for candidate in emphasis_pool):
        weight += 0.6
    if any(char in term for char in "+#./") or len(_signature(term)) <= 4:
        weight += 0.2
    return weight


def _score_term_list(
    terms: list[str],
    emphasis_pool: Iterable[str],
    searchable_resume_text: str,
    resume_tokens: set[str],
    *,
    match_threshold: float = 0.55,
) -> tuple[int, list[str], list[str], int]:
    unique_terms = _unique_terms(terms)
    if not unique_terms:
        return 100, [], [], 0

    total_weight = 0.0
    matched_weight = 0.0
    matched: list[str] = []
    missing: list[str] = []
    signal_count = 0

    for term in unique_terms:
        weight = _term_weight(term, emphasis_pool)
        total_weight += weight
        term_score = _term_match_score(term, searchable_resume_text, resume_tokens)
        matched_weight += weight * term_score
        if term_score >= match_threshold:
            matched.append(term)
            signal_count += 1
        else:
            missing.append(term)

    score = int((matched_weight / total_weight) * 100 + 0.5) if total_weight else 100
    return max(0, min(100, score)), matched, missing, signal_count


def _responsibility_coverage(responsibilities: list[str], searchable_resume_text: str, resume_tokens: set[str]) -> int:
    unique_responsibilities = _unique_terms(responsibilities)
    if not unique_responsibilities:
        return 75

    total_ratio = 0.0
    for responsibility in unique_responsibilities:
        phrase_score = _term_match_score(responsibility, searchable_resume_text, resume_tokens)
        tokens = list(dict.fromkeys(_primary_tokens(responsibility)))
        if not tokens:
            total_ratio += max(0.65, phrase_score)
            continue

        hits = sum(1 for token in tokens if token in resume_tokens)
        token_ratio = hits / len(tokens)
        total_ratio += max(phrase_score, min(1.0, token_ratio * 1.2))

    return int((total_ratio / len(unique_responsibilities)) * 100 + 0.5)


def _title_alignment(job_title: str, searchable_resume_text: str, resume_tokens: set[str]) -> int:
    if not job_title.strip():
        return 75

    title_score = _term_match_score(job_title, searchable_resume_text, resume_tokens)
    title_tokens = list(dict.fromkeys(_primary_tokens(job_title)))
    if not title_tokens:
        return int(title_score * 100 + 0.5)

    token_hits = sum(1 for token in title_tokens if token in resume_tokens)
    token_ratio = token_hits / len(title_tokens)
    alignment = max(title_score, min(1.0, token_ratio * 1.15))
    return int(alignment * 100 + 0.5)


def _education_alignment(education_requirement: str, searchable_resume_text: str, resume_tokens: set[str]) -> int:
    if not education_requirement.strip():
        return 80

    requirement_score = _term_match_score(education_requirement, searchable_resume_text, resume_tokens)
    degree_signals = ["b.e", "be", "btech", "mtech", "m.e", "me", "bachelor", "master", "computer science", "information technology", "it"]
    signal_hits = sum(
        1 for signal in degree_signals
        if _term_match_score(signal, searchable_resume_text, resume_tokens) >= 0.55
    )
    signal_ratio = signal_hits / len(degree_signals)
    alignment = max(requirement_score, min(1.0, 0.45 + signal_ratio))
    return int(alignment * 100 + 0.5)


def _career_level_alignment(experience_years: int, searchable_resume_text: str, resume_tokens: set[str]) -> int:
    if experience_years <= 0:
        return 80

    markers_present = any(marker in resume_tokens for marker in EARLY_CAREER_MARKERS)
    if experience_years <= 2:
        return 92 if markers_present else 78

    if experience_years <= 4:
        return 72 if markers_present else 58

    return 48 if markers_present else 40


def _formatting_score(resume_text: str) -> int:
    lower = resume_text.lower()
    has_sections = sum(1 for marker in ("summary", "skills", "experience", "project", "education") if marker in lower)
    has_bullets = "\\item" in resume_text or bool(re.search(r"^\s*[-*•]", resume_text, flags=re.MULTILINE))
    has_metrics = bool(re.search(r"\b\d+(?:\.\d+)?%|\b\d+[kKmM]?\+?", resume_text))
    single_column_signals = "paracol" not in lower or "setcolumnwidth" in lower

    score = 72
    score += min(has_sections, 5) * 4
    score += 6 if has_bullets else 0
    score += 8 if has_metrics else 0
    score += 4 if single_column_signals else 0
    return max(60, min(96, score))


def _scanner_style_score(raw_score: int, signal_count: int, *, bias: float, scale: float) -> int:
    if raw_score <= 0:
        return 0

    boosted = (raw_score * scale) + bias
    if signal_count >= 3:
        boosted += 4
    if signal_count >= 6:
        boosted += 4
    if signal_count >= 10:
        boosted += 4
    return int(max(0, min(100, boosted)) + 0.5)


def _build_breakdown(
    skills_score: int,
    keyword_score: int,
    experience_score: int,
    formatting_score: int,
    matched_skills: list[str],
    missing_skills: list[str],
    matched_keywords: list[str],
    missing_keywords: list[str],
) -> ScoreBreakdown:
    skills_details = (
        f"Scanner-style hard-skill coverage matched {len(matched_skills)} skills. Biggest gaps: {', '.join(missing_skills[:4]) or 'none'}."
    )
    keyword_details = (
        f"Keyword and phrasing coverage matched {len(matched_keywords)} terms. Biggest gaps: {', '.join(missing_keywords[:4]) or 'none'}."
    )
    experience_details = (
        "Experience relevance blends responsibility overlap, job-title alignment, education fit, and early-career level alignment."
    )
    formatting_details = (
        "Formatting score checks for ATS-readable sections, bullet structure, metrics, and parser-friendly layout."
    )

    return ScoreBreakdown(
        skills=ScoreBreakdownItem(score=skills_score, details=skills_details),
        keywords=ScoreBreakdownItem(score=keyword_score, details=keyword_details),
        experience=ScoreBreakdownItem(score=experience_score, details=experience_details),
        formatting=ScoreBreakdownItem(score=formatting_score, details=formatting_details),
    )


async def score_resume(
    llm: LLMProvider,
    resume_text: str,
    jd_analysis: JDAnalysis,
) -> ATSScore:
    """Score a resume against extracted JD requirements."""
    del llm  # Scoring is deterministic so provider choice does not skew ATS results.

    searchable_resume_text = _searchable_resume_text(resume_text)
    resume_tokens = set(_content_tokens(searchable_resume_text))

    keyword_terms = _unique_terms(jd_analysis.keywords + jd_analysis.preferred_skills)
    emphasis_terms = _unique_terms(jd_analysis.keywords + jd_analysis.tech_stack + jd_analysis.required_skills)

    required_raw, matched_skills, missing_skills, required_signal_count = _score_term_list(
        jd_analysis.required_skills,
        emphasis_terms,
        searchable_resume_text,
        resume_tokens,
    )
    tech_raw, _, _, tech_signal_count = _score_term_list(
        jd_analysis.tech_stack,
        jd_analysis.required_skills,
        searchable_resume_text,
        resume_tokens,
    )
    keyword_raw, matched_keywords, missing_keywords, keyword_signal_count = _score_term_list(
        keyword_terms,
        jd_analysis.required_skills + jd_analysis.tech_stack,
        searchable_resume_text,
        resume_tokens,
        match_threshold=0.52,
    )

    title_score = _title_alignment(jd_analysis.job_title, searchable_resume_text, resume_tokens)
    education_score = _education_alignment(jd_analysis.education, searchable_resume_text, resume_tokens)
    career_level_score = _career_level_alignment(jd_analysis.experience_years, searchable_resume_text, resume_tokens)
    responsibility_score = _responsibility_coverage(jd_analysis.responsibilities, searchable_resume_text, resume_tokens)

    skills_raw = int((required_raw * 0.75) + (tech_raw * 0.25) + 0.5)
    skills_signal_count = max(required_signal_count, len(matched_skills)) + max(0, tech_signal_count // 2)
    skills_score = _scanner_style_score(skills_raw, skills_signal_count, bias=12, scale=0.82)

    keyword_score = _scanner_style_score(keyword_raw, keyword_signal_count, bias=10, scale=0.84)

    experience_raw = int(
        (responsibility_score * 0.40)
        + (title_score * 0.20)
        + (education_score * 0.10)
        + (career_level_score * 0.10)
        + (skills_raw * 0.15)
        + (keyword_raw * 0.05)
        + 0.5
    )
    experience_signal_count = (
        len(matched_skills)
        + int(title_score >= 60)
        + int(education_score >= 60)
        + int(career_level_score >= 75)
    )
    experience_score = _scanner_style_score(experience_raw, experience_signal_count, bias=12, scale=0.80)

    formatting_score = _formatting_score(resume_text)
    overall_score = int(
        (skills_score * 0.38)
        + (keyword_score * 0.24)
        + (experience_score * 0.23)
        + (formatting_score * 0.15)
        + 0.5
    )

    breakdown = _build_breakdown(
        skills_score,
        keyword_score,
        experience_score,
        formatting_score,
        matched_skills,
        missing_skills,
        matched_keywords,
        missing_keywords,
    )

    return ATSScore(
        overall_score=max(0, min(100, overall_score)),
        skills_match_pct=skills_score,
        keyword_match_pct=keyword_score,
        experience_relevance_pct=experience_score,
        missing_skills=missing_skills,
        missing_keywords=missing_keywords,
        matched_skills=matched_skills,
        matched_keywords=matched_keywords,
        breakdown=breakdown,
    )
