"""Build a roadmap from current ATS match rate to 90+ and 100 targets."""
from __future__ import annotations

from backend.models import ATSScore, JDAnalysis, ResumeOptimization, ScoreRoadmap, ScoreRoadmapAction


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _contains_term(items: list[str], term: str) -> bool:
    needle = _normalize(term)
    return any(_normalize(item) == needle for item in items)


def _safe_actions(original_score: ATSScore, optimized_score: ATSScore, optimization: ResumeOptimization) -> list[ScoreRoadmapAction]:
    actions: list[ScoreRoadmapAction] = []

    skill_delta = max(0, optimized_score.skills_match_pct - original_score.skills_match_pct)
    keyword_delta = max(0, optimized_score.keyword_match_pct - original_score.keyword_match_pct)
    experience_delta = max(0, optimized_score.experience_relevance_pct - original_score.experience_relevance_pct)

    if optimization.summary_rewrite:
        actions.append(
            ScoreRoadmapAction(
                title="Apply the optimized summary rewrite",
                detail="The summary is tuned to mirror the JD title, core tools, and shortlist-friendly phrasing.",
                action_type="safe_generated",
                term="",
                estimated_points=max(2, min(8, (keyword_delta // 4) or 3)),
            )
        )

    if optimization.experience_rewrites:
        actions.append(
            ScoreRoadmapAction(
                title=f"Apply {len(optimization.experience_rewrites)} JD-aligned bullet rewrites",
                detail="These bullets carry the biggest ATS lift because they add proof, metrics, and exact job phrases.",
                action_type="safe_generated",
                term="",
                estimated_points=max(3, min(12, (experience_delta // 2) or len(optimization.experience_rewrites))),
            )
        )

    if optimization.skills_to_add or optimization.skills_to_reorder:
        actions.append(
            ScoreRoadmapAction(
                title=f"Apply the technical skills cleanup and {len(optimization.skills_to_add)} verified skill additions",
                detail="This moves the highest-priority JD skills into the technical skills section in an ATS-friendly order.",
                action_type="safe_generated",
                term="",
                estimated_points=max(2, min(10, (skill_delta // 2) or max(1, len(optimization.skills_to_add)))),
            )
        )

    if optimization.keywords_to_inject:
        actions.append(
            ScoreRoadmapAction(
                title=f"Inject {len(optimization.keywords_to_inject)} ATS keywords into stronger wording",
                detail="These phrases improve scanner matching when they are naturally supported by the resume content.",
                action_type="safe_generated",
                term="",
                estimated_points=max(1, min(8, (keyword_delta // 3) or (len(optimization.keywords_to_inject) // 2) or 1)),
            )
        )

    return actions


def _remaining_actions(jd_analysis: JDAnalysis, optimized_score: ATSScore) -> list[ScoreRoadmapAction]:
    actions: list[ScoreRoadmapAction] = []

    for skill in optimized_score.missing_skills:
        required = _contains_term(jd_analysis.required_skills, skill)
        in_stack = _contains_term(jd_analysis.tech_stack, skill)
        points = 5 if required and in_stack else 4 if required else 3
        actions.append(
            ScoreRoadmapAction(
                title=f"Add verified proof for {skill}",
                detail="Add this only if you can defend it in projects, experience, certifications, or interview discussion.",
                action_type="user_confirm" if required else "optional_confirm",
                term=skill,
                estimated_points=points,
                proof_required=True,
                required=required,
            )
        )

    for keyword in optimized_score.missing_keywords:
        if _contains_term(optimized_score.missing_skills, keyword):
            continue

        required = _contains_term(jd_analysis.required_skills, keyword) or _contains_term(jd_analysis.tech_stack, keyword)
        points = 3 if required else 2
        actions.append(
            ScoreRoadmapAction(
                title=f"Mirror the exact JD phrase \"{keyword}\"",
                detail="Add this phrase naturally in the summary, skills, or a bullet where it is already truthfully supported.",
                action_type="phrase_tuning",
                term="",
                estimated_points=points,
                proof_required=required,
                required=required,
            )
        )

    actions.sort(key=lambda action: (action.estimated_points, action.required, action.proof_required), reverse=True)
    return actions


def _actions_for_target(actions: list[ScoreRoadmapAction], gap: int, target_score: int) -> list[ScoreRoadmapAction]:
    if gap <= 0:
        return []

    chosen: list[ScoreRoadmapAction] = []
    covered = 0
    for action in actions:
        chosen.append(action.model_copy(update={"target_score": target_score}))
        covered += action.estimated_points
        if covered >= gap:
            break
    return chosen


def build_score_roadmap(
    jd_analysis: JDAnalysis,
    original_score: ATSScore,
    optimized_score: ATSScore,
    optimization: ResumeOptimization,
) -> ScoreRoadmap:
    """Generate a user-facing roadmap to 90+ and 100 score targets."""
    safe_actions = _safe_actions(original_score, optimized_score, optimization)
    remaining_actions = _remaining_actions(jd_analysis, optimized_score)

    gap_to_90 = max(0, 90 - optimized_score.overall_score)
    gap_to_100 = max(0, 100 - optimized_score.overall_score)
    likely_max_score = min(100, optimized_score.overall_score + sum(action.estimated_points for action in remaining_actions))

    blockers = [
        action.title.replace("Add verified proof for ", "")
        for action in remaining_actions
        if action.required and action.proof_required
    ]

    return ScoreRoadmap(
        current_score=original_score.overall_score,
        projected_score=optimized_score.overall_score,
        likely_max_score=likely_max_score,
        gap_to_90=gap_to_90,
        gap_to_100=gap_to_100,
        safe_actions=safe_actions,
        target_90_actions=_actions_for_target(remaining_actions, gap_to_90, 90),
        target_100_actions=_actions_for_target(remaining_actions, gap_to_100, 100),
        blockers=blockers[:8],
    )
