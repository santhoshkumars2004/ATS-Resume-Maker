"""LaTeX editor — applies structured JSON edits to .tex files."""
import re
from pathlib import Path

from backend.models import ResumeOptimization


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
    if optimization.skills_to_reorder:
        content = _replace_skills(content, optimization.skills_to_reorder, optimization.skills_to_add)

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


def _replace_skills(content: str, reordered_skills: list[str], skills_to_add: list[str]) -> str:
    """Replace the skills section with reordered and new skills."""
    all_skills = list(reordered_skills)
    for skill in skills_to_add:
        if skill not in all_skills:
            all_skills.append(skill)

    begin_marker = "%%BEGIN_SKILLS%%"
    end_marker = "%%END_SKILLS%%"
    begin_idx = content.find(begin_marker)
    end_idx = content.find(end_marker)
    if begin_idx == -1 or end_idx == -1:
        return content

    section_content = content[begin_idx:end_idx]
    categories = _categorize_skills(all_skills)
    
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


def _categorize_skills(skills: list[str]) -> dict[str, list[str]]:
    """Auto-categorize skills into sensible groups."""
    categories = {
        "Languages": [],
        "Frameworks": [],
        "DevOps \\& Cloud": [],
        "Databases": [],
        "Tools \\& Practices": [],
    }

    lang_keywords = {"python", "javascript", "typescript", "java", "go", "rust", "c++", "c#", "ruby", "sql", "r", "scala", "kotlin", "swift"}
    framework_keywords = {"react", "angular", "vue", "next.js", "fastapi", "django", "flask", "spring", "express", "node.js", "svelte"}
    devops_keywords = {"docker", "kubernetes", "ci/cd", "jenkins", "github actions", "terraform", "ansible", "aws", "gcp", "azure", "helm", "argocd"}
    db_keywords = {"postgresql", "mysql", "mongodb", "redis", "elasticsearch", "dynamodb", "cassandra", "sqlite"}

    for skill in skills:
        skill_lower = skill.lower().strip()
        if skill_lower in lang_keywords:
            categories["Languages"].append(skill)
        elif skill_lower in framework_keywords:
            categories["Frameworks"].append(skill)
        elif skill_lower in devops_keywords:
            categories["DevOps \\& Cloud"].append(skill)
        elif skill_lower in db_keywords:
            categories["Databases"].append(skill)
        else:
            categories["Tools \\& Practices"].append(skill)

    # Remove empty categories
    return {k: v for k, v in categories.items() if v}
