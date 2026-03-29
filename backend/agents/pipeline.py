"""AG2 Multi-Agent Pipeline — orchestrates the full resume optimization flow."""
from pathlib import Path
from time import perf_counter

from backend.llm.base import LLMProvider
from backend.logging_utils import log_event
from backend.models import OptimizeResponse
from backend.agents.jd_analyzer import analyze_jd
from backend.agents.ats_scorer import score_resume
from backend.agents.score_roadmap import build_score_roadmap
from backend.agents.resume_optimizer import optimize_resume
from backend.agents.latex_compiler_agent import compile_optimized_resume
from backend.rag.retriever import retrieve_relevant_experience


async def run_pipeline(
    llm: LLMProvider,
    job_description: str,
    company_name: str,
    template_path: str | Path = "data/sample_resume.tex",
    output_dir: str | Path = "output",
    user_output_root: str | Path | None = None,
    is_pdf: bool = False,
    run_id: str = "pipeline",
    provider_name: str = "unknown",
) -> OptimizeResponse:
    """Run the full ATS optimization pipeline.

    Supports both LaTeX (.tex) and PDF (.pdf) resume inputs.

    Flow: JD Analysis → ATS Scoring → RAG Retrieval → Optimization → Compile → Re-Score

    Args:
        llm: The LLM provider to use.
        job_description: Raw job description text.
        company_name: Target company name.
        template_path: Path to the resume template (LaTeX or PDF).
        output_dir: Directory for output files.
        is_pdf: Whether the input is a PDF file.

    Returns:
        OptimizeResponse with all results.
    """
    template_path = Path(template_path)
    if not template_path.exists():
        return OptimizeResponse(
            jd_analysis={},
            original_score={},
            optimization={},
            optimized_score={},
            status="error",
            message=f"Resume template not found: {template_path}",
        )

    log_event(
        run_id,
        "PIPELINE",
        f"starting optimization | provider={provider_name} resume={template_path.name} input_type={'pdf' if is_pdf else 'tex'}",
    )

    # Read the resume content based on format
    pdf_sections = {}
    if is_pdf or template_path.suffix.lower() == ".pdf":
        from backend.pdf.parser import extract_text_from_pdf, extract_sections_from_pdf
        log_event(run_id, "RESUME", f"detected PDF input | path={template_path}")
        resume_text = extract_text_from_pdf(template_path)
        pdf_sections = extract_sections_from_pdf(template_path)
        log_event(run_id, "RESUME", f"extracted {len(resume_text)} characters across {len(pdf_sections)} sections")
    else:
        from backend.latex.parser import get_full_content
        resume_text = get_full_content(template_path)
        log_event(run_id, "RESUME", f"loaded LaTeX template | chars={len(resume_text)} path={template_path}")

    if not resume_text.strip():
        return OptimizeResponse(
            jd_analysis={},
            original_score={},
            optimization={},
            optimized_score={},
            status="error",
            message="Could not extract text from the resume. Please upload a valid PDF or .tex file.",
        )

    # ── Agent 1: JD Analyzer ─────────────────────────────────
    stage_started = perf_counter()
    log_event(run_id, "AGENT-1", "analyzing job description")
    jd_analysis = await analyze_jd(llm, job_description, company_name)
    log_event(
        run_id,
        "AGENT-1",
        f"completed in {perf_counter() - stage_started:.2f}s | title={jd_analysis.job_title or 'unknown'} required_skills={len(jd_analysis.required_skills)} keywords={len(jd_analysis.keywords)}",
    )

    # ── Agent 2: ATS Scorer (original) ───────────────────────
    stage_started = perf_counter()
    log_event(run_id, "AGENT-2", "scoring original resume")
    original_score = await score_resume(llm, resume_text, jd_analysis)
    log_event(
        run_id,
        "AGENT-2",
        f"completed in {perf_counter() - stage_started:.2f}s | overall={original_score.overall_score}/100 skills={original_score.skills_match_pct}% keywords={original_score.keyword_match_pct}% missing_skills={len(original_score.missing_skills)} missing_keywords={len(original_score.missing_keywords)}",
    )

    # ── RAG Retrieval ────────────────────────────────────────
    rag_context = await retrieve_relevant_experience(jd_analysis, run_id=run_id)

    # ── Agent 3: Resume Optimizer ────────────────────────────
    stage_started = perf_counter()
    log_event(run_id, "AGENT-3", "generating resume optimizations")
    optimization = await optimize_resume(
        llm, resume_text, jd_analysis, original_score, rag_context
    )
    log_event(
        run_id,
        "AGENT-3",
        f"completed in {perf_counter() - stage_started:.2f}s | skills_to_add={len(optimization.skills_to_add)} rewrites={len(optimization.experience_rewrites)} keywords_to_inject={len(optimization.keywords_to_inject)}",
    )

    # ── Agent 4: Generate Output ─────────────────────────────
    stage_started = perf_counter()
    log_event(run_id, "AGENT-4", "generating optimized resume output")

    if is_pdf or template_path.suffix.lower() == ".pdf":
        # PDF → PDF workflow (no tectonic needed)
        compile_result = await _compile_pdf_output(
            pdf_sections, optimization, output_dir, company_name, run_id
        )
    else:
        # LaTeX → PDF workflow
        compile_result = await compile_optimized_resume(
            template_path, optimization, output_dir, company_name, run_id
        )

    output_root = Path(user_output_root or output_dir)
    pdf_path = compile_result.get("pdf_path", "")
    tex_path = compile_result.get("tex_path", "")
    log_path = compile_result.get("log_path", "")
    run_output_dir = compile_result.get("output_dir", str(output_dir))

    def _relative(value: str) -> str:
        if not value:
            return ""
        try:
            return Path(value).resolve().relative_to(output_root.resolve()).as_posix()
        except ValueError:
            return Path(value).name

    pdf_filename = Path(pdf_path).name if pdf_path else ""
    pdf_relative = _relative(pdf_path)
    pdf_url = f"/api/download/{pdf_relative}" if pdf_relative else ""

    if not compile_result["compilation_success"]:
        err = compile_result.get("error", "Unknown error")
        log_event(run_id, "AGENT-4", f"completed in {perf_counter() - stage_started:.2f}s | compilation_issue={err}")
    else:
        log_event(
            run_id,
            "AGENT-4",
            f"completed in {perf_counter() - stage_started:.2f}s | pdf={compile_result.get('pdf_path', '')}",
        )

    # ── Agent 2 (re-run): Score optimized resume ─────────────
    stage_started = perf_counter()
    log_event(run_id, "AGENT-2B", "scoring optimized resume")
    optimized_text = compile_result.get("modified_content", resume_text)
    optimized_score = await score_resume(llm, optimized_text, jd_analysis)
    improvement = optimized_score.overall_score - original_score.overall_score
    score_roadmap = build_score_roadmap(jd_analysis, original_score, optimized_score, optimization)
    log_event(
        run_id,
        "AGENT-2B",
        f"completed in {perf_counter() - stage_started:.2f}s | overall={optimized_score.overall_score}/100 improvement={improvement:+d}",
    )

    # Build response
    status = "success" if compile_result["compilation_success"] else "partial"
    message = ""
    if not compile_result["compilation_success"]:
        message = compile_result.get("error", "Compilation failed.")

    log_event(
        run_id,
        "PIPELINE",
        f"finished | status={status} pdf_filename={pdf_filename or 'none'} message={message or 'ok'}",
    )

    return OptimizeResponse(
        jd_analysis=jd_analysis,
        original_score=original_score,
        optimization=optimization,
        optimized_score=optimized_score,
        score_roadmap=score_roadmap,
        pdf_filename=pdf_filename,
        pdf_url=pdf_url,
        tex_path=_relative(tex_path),
        pdf_path=pdf_relative,
        log_path=_relative(log_path),
        output_dir=_relative(run_output_dir),
        status=status,
        message=message,
    )


async def _compile_pdf_output(
    sections: dict[str, str],
    optimization,
    output_dir: str | Path,
    company_name: str,
    run_id: str | None = None,
) -> dict:
    """Generate a PDF from parsed sections + optimization edits."""
    from backend.pdf.generator import generate_optimized_pdf

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_company = company_name.lower().replace(" ", "_").replace("/", "_")[:30]
    pdf_filename = f"resume_{safe_company}.pdf"
    output_path = output_dir / pdf_filename

    try:
        # Convert optimization model to dict
        opt_dict = optimization.model_dump() if hasattr(optimization, "model_dump") else optimization.__dict__

        generate_optimized_pdf(sections, opt_dict, output_path, company_name)
        if run_id:
            log_event(run_id, "COMPILER", f"generated PDF from parsed PDF input | path={output_path}")

        # Build the modified text for re-scoring
        modified_text = sections.get("full_text", "")
        for rewrite in opt_dict.get("experience_rewrites", []):
            if rewrite.get("original") and rewrite.get("replacement"):
                modified_text = modified_text.replace(rewrite["original"], rewrite["replacement"])
        if opt_dict.get("summary_rewrite"):
            summary_key = next((k for k in ["summary", "professional", "profile"] if k in sections), None)
            if summary_key and sections[summary_key]:
                modified_text = modified_text.replace(sections[summary_key], opt_dict["summary_rewrite"])

        return {
            "compilation_success": True,
            "pdf_filename": pdf_filename,
            "pdf_path": str(output_path),
            "log_path": "",
            "output_dir": str(output_dir),
            "modified_content": modified_text,
            "error": None,
        }
    except Exception as e:
        if run_id:
            log_event(run_id, "COMPILER", f"PDF generation failed | error={e}")
        return {
            "compilation_success": False,
            "pdf_filename": "",
            "pdf_path": "",
            "tex_path": "",
            "log_path": "",
            "output_dir": str(output_dir),
            "modified_content": sections.get("full_text", ""),
            "error": str(e),
        }
