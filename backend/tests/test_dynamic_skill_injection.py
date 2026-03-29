from backend.agents.review import filter_optimization_for_review
from backend.latex.editor import apply_edits
from backend.models import ResumeOptimization, ReviewSelection


def test_review_keeps_keywords_when_skills_are_applied():
    optimization = ResumeOptimization(
        skills_to_add=["Grafana"],
        skills_to_reorder=["Python"],
        keywords_to_inject=["Prometheus", "Kubernetes"],
    )
    selection = ReviewSelection(
        apply_skills=True,
        approved_skills_to_add=["Grafana"],
    )

    reviewed = filter_optimization_for_review(optimization, selection)

    assert reviewed.skills_to_add == ["Grafana"]
    assert reviewed.keywords_to_inject == ["Prometheus", "Kubernetes"]


def test_editor_expands_grouped_phrases_into_atomic_skills():
    optimization = ResumeOptimization(
        skills_to_add=[
            "Monitoring tools (Grafana / Prometheus / Datadog)",
            "Cloud platforms (AWS / Azure / GCP)",
            "PagerDuty",
        ],
        keywords_to_inject=[
            "Networking concepts (TCP/IP, DNS, HTTP/HTTPS)",
            "Containers and Kubernetes",
        ],
    )

    content = apply_edits("data/sample_resume.tex", optimization)

    for term in (
        "Grafana",
        "Prometheus",
        "Datadog",
        "AWS",
        "Azure",
        "GCP",
        "PagerDuty",
        "TCP/IP",
        "DNS",
        "HTTP/HTTPS",
        "Containers",
        "Kubernetes",
    ):
        assert term in content


def test_editor_filters_non_skill_noise_and_grouped_labels():
    optimization = ResumeOptimization(
        skills_to_add=[
            "Languages: Python, Java",
            "Frameworks: Fastapi, Django, Express, React.js",
            "Entry-level",
            "Software Engineer",
            "Develop",
            "Maintain",
            "Collaboration",
            "Requirements clarification",
            "REST API",
        ],
        keywords_to_inject=[
            "Application development",
            "Software development",
            "Code readability and maintainability",
            "Debugging",
        ],
    )

    content = apply_edits("data/sample_resume.tex", optimization)
    start = content.index("%%BEGIN_SKILLS%%")
    end = content.index("%%END_SKILLS%%")
    skills_section = content[start:end]

    assert "Languages: Python" not in skills_section
    assert "Frameworks: Fastapi" not in skills_section
    assert "Entry-level" not in skills_section
    assert "Software Engineer" not in skills_section
    assert "Develop" not in skills_section
    assert "Maintain" not in skills_section
    assert "Collaboration" not in skills_section
    assert "Requirements clarification" not in skills_section
    assert "Application development" not in skills_section
    assert "Software development" not in skills_section
    assert "Code readability and maintainability" not in skills_section
    assert "Debugging" in skills_section
