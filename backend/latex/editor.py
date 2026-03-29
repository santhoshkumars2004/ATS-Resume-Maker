"""LaTeX editor — applies structured JSON edits to .tex files."""
import re
from pathlib import Path

from backend.models import ResumeOptimization


SKILL_LIMITS = {
    "Languages": 6,
    "Frontend": 4,
    "Backend": 5,
    "Frameworks": 5,
    "Databases": 4,
    "Tools \\& DevOps": 7,
    "DevOps \\& Cloud": 6,
    "AI \\& Automation": 6,
    "Core Competencies": 6,
}

SOFT_SKILL_PATTERNS = {
    "communication skills",
    "interpersonal skills",
    "quick learning ability",
    "quick learner",
    "problem solving",
    "problem solving & debugging",
    "problem solving and debugging",
    "problem-solving",
    "problem-solving skills",
    "logical thinking",
}

SKILL_CANONICAL_NAMES = {
    "react": "React.js",
    "node": "Node.js",
    "nodejs": "Node.js",
    "express": "Express",
    "expressjs": "Express",
    "fastapi": "FastAPI",
    "django": "Django",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "python": "Python",
    "java": "Java",
    "c": "C",
    "c++": "C++",
    "cpp": "C++",
    "sql": "SQL",
    "html": "HTML5",
    "html5": "HTML5",
    "css": "CSS3",
    "css3": "CSS3",
    "html/css": "HTML/CSS",
    "rest api": "REST API",
    "rest apis": "REST API",
    "jira": "JIRA",
    "github": "GitHub",
    "git": "Git",
    "mcp": "MCP Server",
    "mcp server": "MCP Server",
    "llm pipelines": "LLM Pipelines",
    "prompt engineering": "Prompt Engineering",
    "playwright": "Playwright",
    "websockets": "WebSockets",
    "junit": "JUnit",
    "unit testing": "Unit Testing",
    "integration testing": "Integration Testing",
    "system testing": "System Testing",
    "code reviews": "Code Reviews",
    "debugging": "Debugging",
    "aws cli": "AWS CLI",
    "nosql": "NoSQL",
    "bootstrap": "Bootstrap",
    "foundation": "Foundation",
    "tailwind": "Tailwind CSS",
    "tailwind css": "Tailwind CSS",
    "css frameworks": "CSS Frameworks",
    "front-end": "Front-End Development",
    "front end": "Front-End Development",
    "frontend": "Front-End Development",
    "responsive ui design": "Responsive UI Design",
    "defect fixing": "Defect Fixing",
    "performance optimization": "Performance Optimization",
    "logical design concepts": "Logical Design Concepts",
    "data structures": "Data Structures",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "containers": "Containers",
    "containerization": "Containers",
    "grafana": "Grafana",
    "prometheus": "Prometheus",
    "datadog": "Datadog",
    "linux": "Linux",
    "shell": "Shell",
    "bash": "Shell",
    "tcp/ip": "TCP/IP",
    "dns": "DNS",
    "http/https": "HTTP/HTTPS",
    "observability": "Observability",
    "monitoring": "Monitoring",
    "incident management": "Incident Management",
    "on-call": "On-Call Availability",
    "on-call availability": "On-Call Availability",
    "night shift willingness": "Night Shift Willingness",
    "sre": "SRE",
    "site reliability engineering": "SRE",
}

SKILL_STYLE_OVERRIDES = {
    "react js": "React.js",
    "node js": "Node.js",
    "node.js": "Node.js",
    "express js": "Express",
    "postgres sql": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "github actions": "GitHub Actions",
    "ci/cd": "CI/CD",
    "ai/ml": "AI/ML",
    "gen ai": "Generative AI",
    "generative ai": "Generative AI",
    "llm": "LLM",
    "rag": "RAG",
    "sre": "SRE",
    "tcp/ip": "TCP/IP",
    "http/https": "HTTP/HTTPS",
    "ui": "UI",
    "ux": "UX",
    "aws": "AWS",
    "gcp": "GCP",
    "dns": "DNS",
    "sql": "SQL",
    "nosql": "NoSQL",
}

CATEGORY_SIGNAL_PATTERNS = {
    "Languages": (
        r"\b(java|javascript|typescript|python|golang|go|rust|ruby|php|kotlin|swift|scala|c\+\+|c#|c|sql)\b",
    ),
    "Frontend": (
        r"\b(html5?|css3?|react|angular|vue|frontend|front-end|ui|ux|tailwind|bootstrap|foundation)\b",
    ),
    "Backend": (
        r"\b(node|express|fastapi|django|flask|spring|backend|rest api|restful api|graphql|microservice|api)\b",
    ),
    "Databases": (
        r"\b(postgres|postgresql|mysql|mongodb|redis|database|databases|snowflake|bigquery|warehouse|etl|nosql|chromadb)\b",
    ),
    "Tools \\& DevOps": (
        r"\b(aws|azure|gcp|docker|kubernetes|terraform|ansible|grafana|prometheus|datadog|splunk|elastic|elk|linux|shell|bash|dns|tcp/ip|http/https|network|networking|containers?|incident|on-call|observability|monitoring|sre|site reliability|ci/cd|github actions)\b",
    ),
    "AI \\& Automation": (
        r"\b(ai/ml|ai|ml|llm|rag|generative ai|gen ai|langchain|prompt engineering|nlp|machine learning|automation)\b",
    ),
    "Core Competencies": (
        r"\b(oop|data structures|logical design concepts|performance optimization|defect fixing|problem solving|analytical)\b",
    ),
}

GENERIC_SKILL_PREFIX_PATTERN = re.compile(
    r"^(?:solid|strong|hands-on|practical|foundational|working|good|basic)\s+"
    r"(?:(?:understanding|knowledge|proficiency|experience|exposure|familiarity)\s+(?:of|with|in)\s+)?",
    flags=re.IGNORECASE,
)

GENERIC_SKILL_SUFFIX_PATTERN = re.compile(
    r"\b(?:tools?|platforms?|concepts?|principles?|fundamentals?|skills?|knowledge|experience|exposure)\b$",
    flags=re.IGNORECASE,
)

CATEGORY_PREFIX_PATTERN = re.compile(
    r"^(?:languages|frontend|backend|frameworks|databases|tools(?:\s*&\s*|\s+and\s+)?devops|"
    r"tools(?:\s*&\s*|\s+and\s+)?platforms|core|core competencies|testing|devops(?:\s*&\s*cloud)?|"
    r"ai(?:\s*&\s*automation)?|competencies)\s*:\s*",
    flags=re.IGNORECASE,
)

NON_TECHNICAL_SKILL_PATTERNS = (
    re.compile(r"^(?:entry|junior|mid|senior)[-\s]level$", re.IGNORECASE),
    re.compile(r"^(?:software|python|java|frontend|backend|full[- ]stack)?\s*engineer$", re.IGNORECASE),
    re.compile(r"^(?:software|application)\s+development$", re.IGNORECASE),
    re.compile(r"^code readability(?: and maintainability)?$", re.IGNORECASE),
    re.compile(r"^requirements clarification$", re.IGNORECASE),
    re.compile(r"^collaboration$", re.IGNORECASE),
    re.compile(r"^(?:develop|maintain|build|support|assist|document|analyze|design|optimize|test)$", re.IGNORECASE),
)


def apply_edits(tex_path: str | Path, optimization: ResumeOptimization) -> str:
    """Apply optimization edits to a LaTeX template.

    Args:
        tex_path: Path to the source .tex file.
        optimization: Structured edits from the Resume Optimizer agent.

    Returns:
        Modified LaTeX content as a string.
    """
    tex_path = Path(tex_path)
    content = tex_path.read_text(encoding="utf-8")

    # 1. Update summary section
    if optimization.summary_rewrite:
        content = _replace_summary(content, optimization.summary_rewrite)

    # 2. Update skills section
    if (
        optimization.skills_to_reorder
        or optimization.skills_to_add
        or optimization.keywords_to_inject
    ):
        content = _replace_skills(
            content,
            optimization.skills_to_reorder,
            optimization.skills_to_add,
            optimization.keywords_to_inject,
        )

    # 3. Apply experience bullet rewrites
    for rewrite in optimization.experience_rewrites:
        if rewrite.original and rewrite.replacement:
            content = content.replace(rewrite.original, rewrite.replacement)

    return content


def save_modified(content: str, output_path: str | Path) -> Path:
    """Save modified LaTeX content to a file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def _replace_summary(content: str, new_summary: str) -> str:
    """Replace the summary section content based on format detection."""
    begin_marker = "%%BEGIN_SUMMARY%%"
    end_marker = "%%END_SUMMARY%%"

    begin_idx = content.find(begin_marker)
    end_idx = content.find(end_marker)
    if begin_idx == -1 or end_idx == -1:
        return content
        
    section_content = content[begin_idx:end_idx]
    
    if "\\begin{onecolentry}" in section_content:
        # Custom user format
        new_section = f"\n\\section{{Objective}}\n\n\\begin{{onecolentry}}\n{new_summary}\n\\end{{onecolentry}}\n"
    else:
        # Default moderncv format
        new_section = f"\n\\section{{Summary}}\n\\cvitem{{}}{{{new_summary}}}\n"
        
    before = content[:begin_idx + len(begin_marker)]
    after = content[end_idx:]
    return before + new_section + after


def _replace_skills(
    content: str,
    reordered_skills: list[str],
    skills_to_add: list[str],
    keywords_to_inject: list[str],
) -> str:
    """Replace the skills section with reordered and new skills."""
    begin_marker = "%%BEGIN_SKILLS%%"
    end_marker = "%%END_SKILLS%%"
    begin_idx = content.find(begin_marker)
    end_idx = content.find(end_marker)
    if begin_idx == -1 or end_idx == -1:
        return content

    section_content = content[begin_idx:end_idx]
    existing_categories = _extract_existing_skill_categories(section_content)
    categories = _categorize_skills(
        reordered_skills,
        skills_to_add,
        keywords_to_inject,
        existing_categories,
    )
    
    if "\\textbf{" in section_content and "\\cvitem" not in section_content:
        # Custom user format
        lines = ["\n\\section{Technical Skills}"]
        for category, skills in categories.items():
            skills_str = ", ".join(skills)
            # Ensure any ampersands in LLM strings are escaped for LaTeX
            skills_str = skills_str.replace("\\&", "&").replace("&", "\\&")
            clean_category = category.replace("\\&", "&").replace("&", "\\&")
            lines.append(f"\\textbf{{{clean_category}:}} {skills_str} \\\\")
        new_section = "\n".join(lines) + "\n"
    else:
        # Default moderncv format
        lines = ["\n\\section{Technical Skills}"]
        for category, skills in categories.items():
            skills_str = ", ".join(skills)
            lines.append(f"\\cvitem{{{category}}}{{{skills_str}}}")
        new_section = "\n".join(lines) + "\n"

    before = content[:begin_idx + len(begin_marker)]
    after = content[end_idx:]
    return before + new_section + after


def _extract_existing_skill_categories(section_content: str) -> dict[str, list[str]]:
    """Parse the current skills section so we preserve its structure."""
    categories: dict[str, list[str]] = {}

    for line in section_content.splitlines():
        stripped = line.strip()
        if not stripped.startswith("\\textbf{"):
            continue

        match = re.match(r"\\textbf\{([^}:]+):\}\s*(.*?)(?:\\\\)?$", stripped)
        if not match:
            continue

        category = match.group(1).strip()
        raw_skills = match.group(2).strip()
        items = [item.strip() for item in raw_skills.split(",") if item.strip()]
        categories[category] = items

    cvitem_pattern = re.compile(r"\\cvitem\{([^}]*)\}\{([^}]*)\}")
    for match in cvitem_pattern.finditer(section_content):
        category = match.group(1).strip()
        raw_skills = match.group(2).strip()
        items = [item.strip() for item in raw_skills.split(",") if item.strip()]
        categories[category] = items

    return categories


def _categorize_skills(
    reordered_skills: list[str],
    skills_to_add: list[str],
    keywords_to_inject: list[str],
    existing_categories: dict[str, list[str]],
) -> dict[str, list[str]]:
    """Categorize only compact, technical skills and preserve the existing layout."""
    category_names = list(existing_categories.keys()) or [
        "Languages",
        "Frontend",
        "Backend",
        "Databases",
        "Tools \\& DevOps",
        "Core Competencies",
    ]

    expanded_reordered_skills = _expand_skill_entries(reordered_skills, allow_unknown=True)
    expanded_skills_to_add = _expand_skill_entries(skills_to_add, allow_unknown=True)
    expanded_keywords = _expand_skill_entries(keywords_to_inject, allow_unknown=False)
    expanded_existing_skills = _expand_skill_entries(sum(existing_categories.values(), []), allow_unknown=True)

    explicit_additions = [*expanded_skills_to_add, *expanded_keywords]
    expanded_explicit_additions = explicit_additions
    explicit_addition_keys = {
        _normalize_skill_name(skill).casefold()
        for skill in expanded_explicit_additions
        if _normalize_skill_name(skill)
    }

    merged_skills = [
        *expanded_reordered_skills,
        *expanded_explicit_additions,
        *expanded_existing_skills,
    ]
    category_names = _ensure_category_names(category_names, merged_skills)

    categories = {name: [] for name in category_names}
    seen = set()

    for raw_skill in merged_skills:
        clean_skill = _normalize_skill_name(raw_skill)
        if not clean_skill:
            continue

        if _is_soft_skill(clean_skill) and clean_skill.casefold() not in explicit_addition_keys:
            continue

        skill_key = clean_skill.casefold()
        if skill_key in seen:
            continue
        seen.add(skill_key)

        category = _select_category(clean_skill, category_names)
        if (
            skill_key in explicit_addition_keys
            and category == _prefer_category(category_names, ["Core Competencies", "Tools \\& DevOps", "Backend"])
            and len(clean_skill.split()) <= 3
        ):
            category = _prefer_category(
                category_names,
                ["Tools \\& DevOps", "DevOps \\& Cloud", "Core Competencies"],
            )
        categories.setdefault(category, []).append(clean_skill)

    compact_categories = {}
    for category in category_names:
        items = categories.get(category, [])
        limit = SKILL_LIMITS.get(category, 6)
        explicit_items = [item for item in items if item.casefold() in explicit_addition_keys]
        fallback_items = [item for item in items if item.casefold() not in explicit_addition_keys]
        remaining_slots = max(0, limit - len(explicit_items))
        limited_items = explicit_items + fallback_items[:remaining_slots]
        if limited_items:
            compact_categories[category] = limited_items

    return compact_categories


def _normalize_skill_name(skill: str) -> str:
    """Normalize model-proposed skill strings into concise display names."""
    normalized = skill.strip().replace("\\&", "&")
    normalized = CATEGORY_PREFIX_PATTERN.sub("", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.strip(" ,.;:")
    if not normalized:
        return ""

    canonical = SKILL_CANONICAL_NAMES.get(normalized.casefold())
    if canonical:
        return canonical

    styled_override = SKILL_STYLE_OVERRIDES.get(normalized.casefold())
    if styled_override:
        return styled_override

    if re.fullmatch(r"[A-Za-z]+/[A-Za-z0-9+]+", normalized):
        return normalized.upper()

    if re.search(r"\.js$", normalized, flags=re.IGNORECASE):
        base = normalized[:-3].strip()
        return f"{base.title()}.js"

    if re.fullmatch(r"[A-Za-z][A-Za-z0-9+#./-]*", normalized) and len(normalized.split()) == 1:
        return normalized[0].upper() + normalized[1:]

    return normalized


def _is_soft_skill(skill: str) -> bool:
    """Exclude generic soft skills from the technical skills section."""
    skill_key = skill.casefold()
    return skill_key in SOFT_SKILL_PATTERNS


def _select_category(skill: str, category_names: list[str]) -> str:
    """Map a skill to the best-fit category from the existing section."""
    skill_key = skill.casefold()

    if skill_key in {"java", "javascript", "typescript", "sql", "python", "c", "c++", "c#"}:
        return _prefer_category(category_names, ["Languages", "Core Competencies"])

    if skill_key in {
        "html5",
        "html/css",
        "css3",
        "react.js",
        "react",
        "bootstrap",
        "foundation",
        "tailwind css",
        "css frameworks",
        "front-end development",
        "responsive ui design",
    }:
        return _prefer_category(category_names, ["Frontend", "Frameworks", "Backend", "Core Competencies"])

    if skill_key in {"express", "fastapi", "node.js", "django", "flask"}:
        return _prefer_category(category_names, ["Backend", "Frameworks", "Frontend", "Core Competencies"])

    if skill_key in {"postgresql", "mysql", "mongodb", "redis", "nosql", "cloud db", "chromadb"} or "database" in skill_key:
        return _prefer_category(category_names, ["Databases", "Core Competencies", "Tools \\& DevOps"])

    if skill_key in {
        "git",
        "github",
        "jira",
        "playwright",
        "unit testing",
        "integration testing",
        "docker",
        "kubernetes",
        "aws",
        "azure",
        "gcp",
        "grafana",
        "prometheus",
        "datadog",
        "monitoring",
        "observability",
        "linux",
        "shell",
        "tcp/ip",
        "dns",
        "http/https",
        "containers",
        "incident management",
        "on-call availability",
        "night shift willingness",
        "sre",
    }:
        return _prefer_category(category_names, ["Tools \\& DevOps", "DevOps \\& Cloud", "Core Competencies"])

    if skill_key in {
        "mcp server",
        "llm pipelines",
        "prompt engineering",
        "rest api",
        "websockets",
        "oop",
        "data structures",
        "logical design concepts",
        "defect fixing",
        "performance optimization",
    }:
        return _prefer_category(category_names, ["Core Competencies", "Backend", "Tools \\& DevOps"])

    for category in (
        "Languages",
        "Frontend",
        "Backend",
        "Databases",
        "Tools \\& DevOps",
        "AI \\& Automation",
        "Core Competencies",
    ):
        if _matches_category_signal(skill_key, category):
            return _prefer_category(
                category_names,
                [category, "Core Competencies", "Tools \\& DevOps", "Backend"],
            )

    return _prefer_category(category_names, ["Core Competencies", "Tools \\& DevOps", "Backend"])


def _prefer_category(category_names: list[str], preferences: list[str]) -> str:
    """Pick the first preferred category that exists; otherwise fall back to the first category."""
    for preferred in preferences:
        if preferred in category_names:
            return preferred
    return category_names[0]


def _has_frontend_skills(skills: list[str]) -> bool:
    frontend_terms = {"html5", "css3", "react", "react.js", "javascript", "typescript"}
    return any(_normalize_skill_name(skill).casefold() in frontend_terms for skill in skills)


def _has_core_skills(skills: list[str]) -> bool:
    core_terms = {"oop", "data structures", "mcp server", "llm pipelines", "prompt engineering", "websockets", "rest api"}
    return any(_normalize_skill_name(skill).casefold() in core_terms for skill in skills)


def _expand_explicit_additions(skills: list[str]) -> list[str]:
    """Break grouped JD phrases into atomic skills so new wording stays dynamic."""
    return _expand_skill_entries(skills, allow_unknown=True)


def _expand_skill_entries(skills: list[str], allow_unknown: bool) -> list[str]:
    """Normalize, split, and filter skills before they reach the LaTeX writer."""
    expanded: list[str] = []
    seen = set()

    for raw_skill in skills:
        for term in _extract_skill_terms(raw_skill):
            if not _should_keep_skill_entry(term, allow_unknown=allow_unknown):
                continue
            key = term.casefold()
            if key in seen:
                continue
            seen.add(key)
            expanded.append(term)

    return expanded


def _extract_skill_terms(raw_skill: str) -> list[str]:
    """Split grouped phrases like 'AWS / Azure / GCP' into reusable atomic terms."""
    normalized = raw_skill.strip().replace("\\&", "&")
    normalized = re.sub(r"\s+", " ", normalized).strip(" ,.;:")
    if not normalized:
        return []

    parts: list[str] = []
    parenthetical_chunks = re.findall(r"\(([^)]*)\)", normalized)
    head = re.sub(r"\([^)]*\)", "", normalized).strip(" ,.;:-")
    has_list_separators = bool(
        re.search(r",|;|\s/\s|\s\|\s|\s+(?:and|or)\s+", normalized, flags=re.IGNORECASE)
    )

    if head and len(head.split()) <= 4 and (parenthetical_chunks or not has_list_separators):
        collapsed_head = _collapse_skill_label(head)
        if collapsed_head:
            parts.append(collapsed_head)

    if parenthetical_chunks:
        for chunk in parenthetical_chunks:
            parts.extend(_split_skill_chunks(chunk))
    elif has_list_separators:
        parts.extend(_split_skill_chunks(normalized))
    else:
        parts.append(normalized)

    cleaned_terms: list[str] = []
    seen = set()
    for part in parts:
        stripped = _strip_skill_wrappers(part)
        if not stripped:
            continue
        clean_term = _normalize_skill_name(stripped)
        if not clean_term:
            continue
        key = clean_term.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned_terms.append(clean_term)

    return cleaned_terms or [_normalize_skill_name(normalized)]


def _split_skill_chunks(text: str) -> list[str]:
    pieces = re.split(r"\s/\s|,|;|\|", text)
    if len(pieces) == 1 and re.search(r"\s+(?:and|or)\s+", text, flags=re.IGNORECASE):
        conjunction_pieces = re.split(r"\s+(?:and|or)\s+", text, flags=re.IGNORECASE)
        stripped_conjunction_pieces = [piece.strip(" ,.;:") for piece in conjunction_pieces if piece.strip(" ,.;:")]
        if stripped_conjunction_pieces and all(_looks_atomic_tech_term(piece) for piece in stripped_conjunction_pieces):
            pieces = stripped_conjunction_pieces
    return [piece.strip(" ,.;:") for piece in pieces if piece.strip(" ,.;:")]


def _strip_skill_wrappers(value: str) -> str:
    stripped = value.strip(" ,.;:-")
    stripped = CATEGORY_PREFIX_PATTERN.sub("", stripped)
    stripped = GENERIC_SKILL_PREFIX_PATTERN.sub("", stripped).strip(" ,.;:-")
    stripped = re.sub(r"^(?:knowledge|experience|exposure|understanding|familiarity)\s+(?:of|with|in)\s+", "", stripped, flags=re.IGNORECASE)
    return stripped.strip(" ,.;:-")


def _collapse_skill_label(value: str) -> str:
    stripped = _strip_skill_wrappers(value)
    stripped = GENERIC_SKILL_SUFFIX_PATTERN.sub("", stripped).strip(" ,.;:-")
    if stripped.casefold() in {"monitoring tools", "monitoring tool"}:
        return "Monitoring"
    if stripped.casefold() in {"cloud platforms", "cloud platform"}:
        return "Cloud"
    if stripped.casefold() in {"networking concepts", "networking concept"}:
        return "Networking"
    return stripped


def _matches_category_signal(skill_key: str, category: str) -> bool:
    return any(re.search(pattern, skill_key) for pattern in CATEGORY_SIGNAL_PATTERNS.get(category, ()))


def _ensure_category_names(category_names: list[str], skills: list[str]) -> list[str]:
    updated = list(category_names)

    if _has_frontend_skills(skills) and "Frontend" not in updated:
        insert_at = 1 if "Languages" in updated else 0
        updated.insert(insert_at, "Frontend")

    for category in ("Backend", "Databases", "Tools \\& DevOps", "AI \\& Automation"):
        if category not in updated and any(_matches_category_signal(_normalize_skill_name(skill).casefold(), category) for skill in skills):
            updated.append(category)

    if _has_core_skills(skills) and "Core Competencies" not in updated:
        updated.append("Core Competencies")

    return updated


def _looks_atomic_tech_term(value: str) -> bool:
    cleaned = _strip_skill_wrappers(value)
    if not cleaned:
        return False

    skill_key = cleaned.casefold()
    if any(_matches_category_signal(skill_key, category) for category in CATEGORY_SIGNAL_PATTERNS):
        return True

    if re.search(r"[./+#]", cleaned):
        return True

    return len(cleaned.split()) == 1 and not _is_soft_skill(cleaned)


def _should_keep_skill_entry(value: str, allow_unknown: bool) -> bool:
    clean = _normalize_skill_name(value)
    if not clean:
        return False

    if _is_soft_skill(clean):
        return False

    lowered = clean.casefold()
    if any(pattern.match(clean) for pattern in NON_TECHNICAL_SKILL_PATTERNS):
        return False

    if any(_matches_category_signal(lowered, category) for category in CATEGORY_SIGNAL_PATTERNS):
        return True

    if lowered in {
        "oop",
        "rest api",
        "mcp server",
        "llm pipelines",
        "prompt engineering",
        "unit testing",
        "integration testing",
        "system testing",
        "debugging",
        "code reviews",
        "aws cli",
        "junit",
    }:
        return True

    if re.search(r"[./+#]", clean):
        return True

    return allow_unknown and len(clean.split()) <= 2
