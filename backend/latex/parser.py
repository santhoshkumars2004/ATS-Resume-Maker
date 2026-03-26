"""LaTeX template parser — extracts editable sections from .tex files."""
import re
from pathlib import Path


# Section marker pattern: %%BEGIN_SECTIONNAME%% ... %%END_SECTIONNAME%%
SECTION_PATTERN = re.compile(
    r"%%BEGIN_(\w+)%%\s*\n(.*?)%%END_\1%%",
    re.DOTALL,
)


def parse_template(tex_path: str | Path) -> dict[str, str]:
    """Parse a LaTeX template and extract marked sections.

    Args:
        tex_path: Path to the .tex file.

    Returns:
        Dict mapping section names (lowercase) to their content.
        e.g. {'skills': '\\section{Technical Skills}\\n...', 'experience': '...'}
    """
    tex_path = Path(tex_path)
    content = tex_path.read_text(encoding="utf-8")

    sections = {}
    for match in SECTION_PATTERN.finditer(content):
        section_name = match.group(1).lower()
        section_content = match.group(2).strip()
        sections[section_name] = section_content

    return sections


def get_full_content(tex_path: str | Path) -> str:
    """Read the full .tex file content."""
    return Path(tex_path).read_text(encoding="utf-8")


def extract_skills(skills_section: str) -> list[str]:
    """Extract individual skills from the skills section.

    Args:
        skills_section: LaTeX content of the skills section.

    Returns:
        Flat list of all skill strings found.
    """
    skills = []
    # Match \cvitem{Category}{Skill1, Skill2, ...}
    cvitem_pattern = re.compile(r"\\cvitem\{[^}]*\}\{([^}]+)\}")
    for match in cvitem_pattern.finditer(skills_section):
        items = [s.strip() for s in match.group(1).split(",")]
        skills.extend(items)
    return skills


def extract_experience_bullets(experience_section: str) -> list[dict]:
    """Extract experience entries and their bullet points.

    Returns:
        List of dicts with 'title', 'company', and 'bullets' keys.
    """
    entries = []
    # Split by \cventry
    entry_pattern = re.compile(
        r"\\cventry\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}\{[^}]*\}\{"
        r"\s*\\begin\{itemize\}(.*?)\\end\{itemize\}\s*\}",
        re.DOTALL,
    )
    for match in entry_pattern.finditer(experience_section):
        bullets_raw = match.group(5)
        bullets = [
            b.strip()
            for b in re.findall(r"\\item\s+(.+?)(?=\\item|\Z)", bullets_raw, re.DOTALL)
        ]
        entries.append({
            "dates": match.group(1).strip(),
            "title": match.group(2).strip(),
            "company": match.group(3).strip(),
            "location": match.group(4).strip(),
            "bullets": [b.strip() for b in bullets if b.strip()],
        })
    return entries
