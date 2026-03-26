"""LaTeX compiler — runs tectonic to produce PDF from .tex files."""
import asyncio
import shutil
from pathlib import Path


async def compile_pdf(tex_path: str | Path, output_dir: str | Path = "output") -> Path:
    """Compile a LaTeX file to PDF using tectonic.

    Args:
        tex_path: Path to the .tex file.
        output_dir: Directory to store the output PDF.

    Returns:
        Path to the generated PDF file.

    Raises:
        RuntimeError: If tectonic is not installed or compilation fails.
    """
    tex_path = Path(tex_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check if tectonic is available
    if not shutil.which("tectonic"):
        raise RuntimeError(
            "tectonic is not installed. Install with: brew install tectonic"
        )

    # Run tectonic
    process = await asyncio.create_subprocess_exec(
        "tectonic",
        str(tex_path),
        "--outdir", str(output_dir),
        "--keep-logs",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_msg = stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"LaTeX compilation failed:\n{error_msg}")

    # Find the produced PDF
    pdf_name = tex_path.stem + ".pdf"
    pdf_path = output_dir / pdf_name

    if not pdf_path.exists():
        raise RuntimeError(
            f"Compilation succeeded but PDF not found at {pdf_path}.\n"
            f"stdout: {stdout.decode()}\nstderr: {stderr.decode()}"
        )

    return pdf_path


async def check_tectonic() -> bool:
    """Check if tectonic is installed and accessible."""
    return shutil.which("tectonic") is not None
