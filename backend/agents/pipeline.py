"""AG2 Multi-Agent Pipeline — orchestrates the full resume optimization flow."""
from pathlib import Path

from backend.llm.base import LLMProvider
from backend.models import OptimizeResponse
from backend.agents.jd_analyzer import analyze_jd
from backend.agents.ats_scorer import score_resume
from backend.agents.resume_optimizer import optimize_resume
from backend.agents.latex_compiler_agent import compile_optimized_resume
from backend.rag.retriever import retrieve_relevant_experience


async def run_pipeline(
    llm: LLMProvider,
    job_description: str,
    company_name: str,
    template_path: str | Path = "data/sample_resume.tex",
    output_dir: str | Path = "output",
    is_pdf: bool = False,
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

    # Read the resume content based on format
    pdf_sections = {}
    if is_pdf or template_path.suffix.lower() == ".pdf":
        from backend.pdf.parser import extract_text_from_pdf, extract_sections_from_pdf
        print("📄 Detected PDF input — extracting text...")
        resume_text = extract_text_from_pdf(template_path)
        pdf_sections = extract_sections_from_pdf(template_path)
        print(f"   → Extracted {len(resume_text)} characters, {len(pdf_sections)} sections")
    else:
        from backend.latex.parser import get_full_content
        resume_text = get_full_content(template_path)

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
    print("🔍 Agent 1: Analyzing job description...")
    jd_analysis = await analyze_jd(llm, job_description, company_name)
    print(f"   → Found {len(jd_analysis.required_skills)} required skills, "
          f"{len(jd_analysis.keywords)} keywords")

    # ── Agent 2: ATS Scorer (original) ───────────────────────
    print("📊 Agent 2: Scoring original resume...")
    original_score = await score_resume(llm, resume_text, jd_analysis)
    print(f"   → Original ATS Score: {original_score.overall_score}/100")

    # ── RAG Retrieval ────────────────────────────────────────
    print("🧠 RAG: Retrieving relevant experience...")
    rag_context = await retrieve_relevant_experience(jd_analysis)
    if rag_context:
        print("   → Found relevant experience from knowledge base")
    else:
        print("   → No RAG context available (knowledge base may be empty)")

    # ── Agent 3: Resume Optimizer ────────────────────────────
    print("✨ Agent 3: Generating optimizations...")
    optimization = await optimize_resume(
        llm, resume_text, jd_analysis, original_score, rag_context
    )
    print(f"   → {len(optimization.skills_to_add)} skills to add, "
          f"{len(optimization.experience_rewrites)} bullets to rewrite")

    # ── Agent 4: Generate Output ─────────────────────────────
    print("📄 Agent 4: Generating optimized resume...")

    if is_pdf or template_path.suffix.lower() == ".pdf":
        # PDF → PDF workflow (no tectonic needed)
        compile_result = await _compile_pdf_output(
            pdf_sections, optimization, output_dir, company_name
        )
    else:
        # LaTeX → PDF workflow
        compile_result = await compile_optimized_resume(
            template_path, optimization, output_dir, company_name
        )

    pdf_filename = compile_result.get("pdf_filename", "")
    pdf_url = f"/api/download/{pdf_filename}" if pdf_filename else ""

    if not compile_result["compilation_success"]:
        err = compile_result.get("error", "Unknown error")
        print(f"   ⚠️  Compilation issue: {err}")
    else:
        print(f"   → PDF generated: {compile_result.get('pdf_path', '')}")

    # ── Agent 2 (re-run): Score optimized resume ─────────────
    print("📊 Agent 2: Scoring optimized resume...")
    optimized_text = compile_result.get("modified_content", resume_text)
    optimized_score = await score_resume(llm, optimized_text, jd_analysis)
    print(f"   → Optimized ATS Score: {optimized_score.overall_score}/100")
    print(f"   → Improvement: +{optimized_score.overall_score - original_score.overall_score} points")

    # Build response
    status = "success" if compile_result["compilation_success"] else "partial"
    message = ""
    if not compile_result["compilation_success"]:
        message = compile_result.get("error", "Compilation failed.")

    return OptimizeResponse(
        jd_analysis=jd_analysis,
        original_score=original_score,
        optimization=optimization,
        optimized_score=optimized_score,
        pdf_filename=pdf_filename,
        pdf_url=pdf_url,
        status=status,
        message=message,
    )


async def _compile_pdf_output(
    sections: dict[str, str],
    optimization,
    output_dir: str | Path,
    company_name: str,
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
            "modified_content": modified_text,
            "error": None,
        }
    except Exception as e:
        return {
            "compilation_success": False,
            "pdf_filename": "",
            "pdf_path": "",
            "tex_path": "",
            "modified_content": sections.get("full_text", ""),
            "error": str(e),
        }
