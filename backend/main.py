"""FastAPI application — main API server for Resume ATS Optimizer."""
import os
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.llm.factory import get_llm_provider
from backend.models import OptimizeRequest, OptimizeResponse
from backend.agents.pipeline import run_pipeline
from backend.rag.ingest import ingest_experience

load_dotenv()

# Directories
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
TEMPLATE_PATH = DATA_DIR / "sample_resume.tex"

# Track uploaded resume (PDF or TEX)
_uploaded_resume: dict = {"path": None, "type": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle events."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    experience_file = DATA_DIR / "experience.json"
    if experience_file.exists():
        print("📚 Ingesting experience data into RAG knowledge base...")
        ingest_experience(experience_file)

    yield
    print("👋 Shutting down Resume ATS Optimizer")


app = FastAPI(
    title="Resume ATS Optimizer",
    description="AI-powered resume optimization for ATS compatibility",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    llm_provider = os.getenv("LLM_PROVIDER", "mock")

    # Check if any resume is loaded (PDF or TEX)
    has_template = TEMPLATE_PATH.exists() or (
        _uploaded_resume["path"] and Path(_uploaded_resume["path"]).exists()
    )
    resume_type = _uploaded_resume["type"] or ("tex" if TEMPLATE_PATH.exists() else None)

    from backend.latex.compiler import check_tectonic
    tectonic_available = await check_tectonic()

    return {
        "status": "healthy",
        "llm_provider": llm_provider,
        "template_loaded": has_template,
        "resume_type": resume_type,
        "tectonic_available": tectonic_available,
    }


@app.post("/api/optimize", response_model=OptimizeResponse)
async def optimize_resume(request: OptimizeRequest):
    """Run the full ATS optimization pipeline.

    Supports both PDF and LaTeX resume inputs.
    """
    # Determine which resume to use
    resume_path = None
    is_pdf = False

    if _uploaded_resume["path"] and Path(_uploaded_resume["path"]).exists():
        resume_path = Path(_uploaded_resume["path"])
        is_pdf = _uploaded_resume["type"] == "pdf"
    elif TEMPLATE_PATH.exists():
        resume_path = TEMPLATE_PATH
        is_pdf = False
    else:
        raise HTTPException(
            status_code=400,
            detail="No resume found. Please upload your resume (PDF or .tex) first.",
        )

    llm = get_llm_provider()

    result = await run_pipeline(
        llm=llm,
        job_description=request.job_description,
        company_name=request.company_name,
        template_path=resume_path,
        output_dir=OUTPUT_DIR,
        is_pdf=is_pdf,
    )

    return result


@app.post("/api/upload-template")
async def upload_template(file: UploadFile = File(...)):
    """Upload a resume file (PDF or LaTeX .tex)."""
    global _uploaded_resume

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    filename = file.filename.lower()
    if not (filename.endswith(".pdf") or filename.endswith(".tex")):
        raise HTTPException(status_code=400, detail="File must be a .pdf or .tex file")

    content = await file.read()

    if filename.endswith(".pdf"):
        # Save PDF resume
        save_path = DATA_DIR / "uploaded_resume.pdf"
        save_path.write_bytes(content)
        _uploaded_resume = {"path": str(save_path), "type": "pdf"}
        file_type = "PDF"
    else:
        # Save LaTeX resume
        TEMPLATE_PATH.write_bytes(content)
        _uploaded_resume = {"path": str(TEMPLATE_PATH), "type": "tex"}
        file_type = "LaTeX"

    return {
        "status": "success",
        "message": f"{file_type} resume '{file.filename}' uploaded successfully",
        "type": file_type.lower(),
    }


@app.post("/api/upload-experience")
async def upload_experience(file: UploadFile = File(...)):
    """Upload an experience database (JSON file)."""
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="File must be a .json file")

    content = await file.read()
    experience_path = DATA_DIR / "experience.json"
    experience_path.write_bytes(content)

    count = ingest_experience(experience_path, reset=True)

    return {
        "status": "success",
        "message": f"Experience database uploaded. {count} documents ingested into RAG.",
    }


@app.get("/api/download/{filename}")
async def download_pdf(filename: str):
    """Download a generated PDF file."""
    safe_filename = Path(filename).name
    file_path = OUTPUT_DIR / safe_filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {safe_filename}")

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=safe_filename,
    )


@app.get("/api/templates")
async def list_templates():
    """List available resume templates."""
    templates = []
    if _uploaded_resume["path"] and Path(_uploaded_resume["path"]).exists():
        p = Path(_uploaded_resume["path"])
        templates.append({
            "name": p.name,
            "path": str(p),
            "type": _uploaded_resume["type"],
            "size": p.stat().st_size,
        })
    elif TEMPLATE_PATH.exists():
        templates.append({
            "name": TEMPLATE_PATH.name,
            "path": str(TEMPLATE_PATH),
            "type": "tex",
            "size": TEMPLATE_PATH.stat().st_size,
        })
    return {"templates": templates}
