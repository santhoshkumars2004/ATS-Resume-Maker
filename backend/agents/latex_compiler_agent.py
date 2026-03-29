"""LaTeX Compiler Agent — applies edits and produces PDF."""
from pathlib import Path

from backend.latex.editor import apply_edits, save_modified
from backend.latex.compiler import compile_pdf
from backend.logging_utils import log_event
from backend.models import ResumeOptimization


async def compile_optimized_resume(
    template_path: str | Path,
    optimization: ResumeOptimization,
    output_dir: str | Path = "output",
    company_name: str = "company",
    run_id: str | None = None,
) -> dict:
    """Apply optimizations to the LaTeX template and compile to PDF.

    Args:
        template_path: Path to the source .tex template.
        optimization: Structured edits to apply.
        output_dir: Directory for output files.
        company_name: Company name for the output filename.

    Returns:
        Dict with 'tex_path', 'pdf_path', and 'modified_content'.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize company name for filename
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in company_name)
    safe_name = safe_name.strip().replace(" ", "_").lower()

    # Apply edits to the template
    modified_content = apply_edits(template_path, optimization)

    # Save modified .tex
    tex_filename = f"resume_{safe_name}.tex"
    modified_tex_path = save_modified(modified_content, output_dir / tex_filename)
    if run_id:
        log_event(run_id, "COMPILER", f"saved modified LaTeX | path={modified_tex_path}")

    # Compile to PDF
    try:
        pdf_path = await compile_pdf(modified_tex_path, output_dir)
        log_path = modified_tex_path.with_suffix(".log")
        if run_id:
            log_event(run_id, "COMPILER", f"compiled PDF successfully | path={pdf_path}")
        return {
            "tex_path": str(modified_tex_path),
            "pdf_path": str(pdf_path),
            "pdf_filename": pdf_path.name,
            "log_path": str(log_path) if log_path.exists() else "",
            "output_dir": str(output_dir),
            "modified_content": modified_content,
            "compilation_success": True,
            "error": None,
        }
    except RuntimeError as e:
        if run_id:
            log_event(run_id, "COMPILER", f"compilation failed | error={e}")
        return {
            "tex_path": str(modified_tex_path),
            "pdf_path": "",
            "pdf_filename": "",
            "log_path": str(modified_tex_path.with_suffix(".log")) if modified_tex_path.with_suffix(".log").exists() else "",
            "output_dir": str(output_dir),
            "modified_content": modified_content,
            "compilation_success": False,
            "error": str(e),
        }
