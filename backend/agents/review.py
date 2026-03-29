"""Helpers for applying only user-approved optimization changes."""
from backend.models import ResumeOptimization, ReviewSelection


def filter_optimization_for_review(
    optimization: ResumeOptimization,
    selection: ReviewSelection,
) -> ResumeOptimization:
    """Build a new optimization object containing only approved changes."""
    approved_skills = {skill.strip() for skill in selection.approved_skills_to_add if skill.strip()}
    rejected_skills = {
        skill.strip()
        for skill in optimization.skills_to_add
        if skill.strip() and skill.strip() not in approved_skills
    }

    filtered_experience = []
    approved_indices = set(selection.approved_experience_indices)
    for index, rewrite in enumerate(optimization.experience_rewrites):
        if index in approved_indices:
            filtered_experience.append(rewrite)

    skills_to_reorder = []
    skills_to_add = []
    if selection.apply_skills:
        original_skill_order = [skill.strip() for skill in optimization.skills_to_add if skill.strip()]
        manual_skill_adds = [
            skill.strip()
            for skill in selection.approved_skills_to_add
            if skill.strip() and skill.strip() not in original_skill_order
        ]
        skills_to_reorder = [
            skill for skill in optimization.skills_to_reorder
            if skill.strip() not in rejected_skills
        ]
        skills_to_add = [skill for skill in optimization.skills_to_add if skill.strip() in approved_skills]
        skills_to_add.extend(manual_skill_adds)

    return ResumeOptimization(
        skills_to_add=skills_to_add,
        skills_to_reorder=skills_to_reorder,
        experience_rewrites=filtered_experience,
        summary_rewrite=optimization.summary_rewrite if selection.apply_summary else "",
        keywords_to_inject=optimization.keywords_to_inject if selection.apply_skills else [],
    )


def has_any_selected_change(optimization: ResumeOptimization) -> bool:
    """Return True when at least one reviewed change remains."""
    return bool(
        optimization.summary_rewrite
        or optimization.skills_to_reorder
        or optimization.skills_to_add
        or optimization.experience_rewrites
    )
