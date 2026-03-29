"""FastAPI application — main API server for Resume ATS Optimizer."""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from pydantic import BaseModel
from backend.agents.ats_scorer import score_resume
from backend.agents.latex_compiler_agent import compile_optimized_resume
from backend.agents.pipeline import _compile_pdf_output, run_pipeline
from backend.agents.review import filter_optimization_for_review, has_any_selected_change
from backend.agents.score_roadmap import build_score_roadmap
from backend.auth_store import (
    AuthUser,
    authenticate_user,
    build_run_output_dir,
    configure_auth_store,
    create_session,
    create_user,
    delete_history_entry,
    delete_session,
    get_history_entry,
    get_user_by_token,
    get_user_template,
    list_history_entries,
    list_user_templates,
    resolve_user_output_path,
    save_history_entry,
    save_user_template_bytes,
    save_user_template_text,
    user_output_dir,
)
from backend.llm.factory import get_llm_provider
from backend.logging_utils import configure_logging, log_event, new_run_id
from backend.llm.registry import get_provider_options, normalize_provider_name
from backend.models import ApplyChangesRequest, OptimizeRequest, OptimizeResponse
from backend.rag.ingest import ingest_experience


class TemplateTextRequest(BaseModel):
    content: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


load_dotenv()

# Directories
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))


def _error_status_code(exc: Exception) -> int:
    """Map known user-fixable provider errors to 400 responses."""
    message = str(exc).lower()
    if "not supported by your current codex login" in message:
        return 400
    if "not supported when using codex with a chatgpt account" in message:
        return 400
    if "did not return valid json" in message:
        return 502
    return 500


def _extract_token(authorization: str | None, query_token: str | None) -> str | None:
    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer" and value.strip():
            return value.strip()
    if query_token:
        return query_token.strip()
    return None


def _relative_artifact_path(base_dir: Path, artifact_path: str) -> str:
    if not artifact_path:
        return ""
    try:
        return Path(artifact_path).resolve().relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return Path(artifact_path).name


async def get_current_user(
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
) -> AuthUser:
    auth_token = _extract_token(authorization, token)
    user = get_user_by_token(auth_token)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


async def get_optional_user(
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
) -> AuthUser | None:
    auth_token = _extract_token(authorization, token)
    return get_user_by_token(auth_token)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle events."""
    configure_logging()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    configure_auth_store(DATA_DIR, OUTPUT_DIR)

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
async def health_check(current_user: AuthUser | None = Depends(get_optional_user)):
    """Health check endpoint."""
    llm_provider = normalize_provider_name(os.getenv("LLM_PROVIDER", "codex"))

    template_path, resume_type = (get_user_template(current_user.id) if current_user else (None, None))
    has_template = bool(template_path and template_path.exists())

    from backend.latex.compiler import check_tectonic
    tectonic_available = await check_tectonic()

    return {
        "status": "healthy",
        "llm_provider": llm_provider,
        "default_provider": llm_provider,
        "available_providers": get_provider_options(),
        "template_loaded": has_template,
        "resume_type": resume_type,
        "tectonic_available": tectonic_available,
        "authenticated": bool(current_user),
        "current_user": (
            {"id": current_user.id, "email": current_user.email, "name": current_user.name}
            if current_user else None
        ),
    }


@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    """Create an account and return a session token."""
    try:
        user = create_user(request.name, request.email, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    token = create_session(user.id)
    return {
        "token": token,
        "user": {"id": user.id, "email": user.email, "name": user.name},
    }


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """Authenticate and return a session token."""
    try:
        user = authenticate_user(request.email, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_session(user.id)
    return {
        "token": token,
        "user": {"id": user.id, "email": user.email, "name": user.name},
    }


@app.post("/api/auth/logout")
async def logout(
    current_user: AuthUser = Depends(get_current_user),
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
):
    """Invalidate the current session token."""
    del current_user
    auth_token = _extract_token(authorization, token)
    if auth_token:
        delete_session(auth_token)
    return {"status": "success"}


@app.get("/api/auth/me")
async def me(current_user: AuthUser = Depends(get_current_user)):
    """Return the current authenticated user."""
    return {"id": current_user.id, "email": current_user.email, "name": current_user.name}


@app.get("/api/history")
async def history(current_user: AuthUser = Depends(get_current_user)):
    """List recent saved optimization runs for the current user."""
    return {"items": list_history_entries(current_user.id)}


@app.get("/api/history/{entry_id}")
async def history_detail(entry_id: int, current_user: AuthUser = Depends(get_current_user)):
    """Return a saved optimization result."""
    entry = get_history_entry(current_user.id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Saved result not found.")
    return entry


@app.delete("/api/history/{entry_id}")
async def history_delete(entry_id: int, current_user: AuthUser = Depends(get_current_user)):
    """Delete a saved optimization result and its artifacts."""
    deleted = delete_history_entry(current_user.id, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved result not found.")
    return {"status": "success"}


@app.post("/api/optimize", response_model=OptimizeResponse)
async def optimize_resume(request: OptimizeRequest, current_user: AuthUser = Depends(get_current_user)):
    """Run the full ATS optimization pipeline.

    Supports both PDF and LaTeX resume inputs.
    """
    run_id = new_run_id()
    # Determine which resume to use
    resume_path, resume_type = get_user_template(current_user.id)
    if not resume_path:
        raise HTTPException(
            status_code=400,
            detail="No resume found. Please upload your resume (PDF or .tex) first.",
        )
    is_pdf = resume_type == "pdf"

    try:
        llm = get_llm_provider(request.provider, request.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    selected_provider = normalize_provider_name(request.provider)
    selected_model = request.model or getattr(llm, "model", None) or "default"
    output_root = user_output_dir(current_user.id)
    run_output_dir = build_run_output_dir(current_user.id, request.company_name, run_id)
    log_event(
        run_id,
        "REQUEST",
        f"optimize requested | provider={selected_provider} model={selected_model} company={request.company_name} resume_type={'pdf' if is_pdf else 'tex'} jd_chars={len(request.job_description)}",
    )

    try:
        result = await run_pipeline(
            llm=llm,
            job_description=request.job_description,
            company_name=request.company_name,
            template_path=resume_path,
            output_dir=run_output_dir,
            user_output_root=output_root,
            is_pdf=is_pdf,
            run_id=run_id,
            provider_name=selected_provider,
        )
    except Exception as exc:
        log_event(run_id, "REQUEST", f"optimization failed | provider={selected_provider} error={exc}")
        raise HTTPException(
            status_code=_error_status_code(exc),
            detail=f"Optimization failed using provider '{selected_provider}': {exc}",
        ) from exc

    result.provider = selected_provider
    result.model = getattr(llm, "model", None) or ""
    save_history_entry(
        user_id=current_user.id,
        company_name=request.company_name,
        provider=result.provider,
        model=result.model,
        original_score=result.original_score.overall_score,
        optimized_score=result.optimized_score.overall_score,
        status=result.status,
        review_applied=result.review_applied,
        result_payload=result.model_dump(),
    )
    log_event(run_id, "REQUEST", f"optimization response sent | status={result.status}")
    return result


@app.post("/api/apply-selected-changes", response_model=OptimizeResponse)
async def apply_selected_changes(request: ApplyChangesRequest, current_user: AuthUser = Depends(get_current_user)):
    """Compile and score only the user-approved changes."""
    run_id = new_run_id()
    resume_path, resume_type = get_user_template(current_user.id)
    if not resume_path:
        raise HTTPException(
            status_code=400,
            detail="No resume found. Please upload your resume (PDF or .tex) first.",
        )
    is_pdf = resume_type == "pdf"

    try:
        llm = get_llm_provider(request.provider, request.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    selected_provider = normalize_provider_name(request.provider)
    selected_model = request.model or getattr(llm, "model", None) or "default"
    reviewed_optimization = filter_optimization_for_review(request.optimization, request.selection)
    output_root = user_output_dir(current_user.id)
    run_output_dir = build_run_output_dir(current_user.id, request.company_name, run_id)

    if not has_any_selected_change(reviewed_optimization):
        raise HTTPException(status_code=400, detail="Select at least one change before applying.")

    log_event(
        run_id,
        "REVIEW",
        f"applying reviewed changes | provider={selected_provider} model={selected_model} summary={request.selection.apply_summary} skills={request.selection.apply_skills} skill_adds={len(request.selection.approved_skills_to_add)} bullets={len(request.selection.approved_experience_indices)}",
    )

    if is_pdf or resume_path.suffix.lower() == ".pdf":
        from backend.pdf.parser import extract_sections_from_pdf

        pdf_sections = extract_sections_from_pdf(resume_path)
        compile_result = await _compile_pdf_output(
            pdf_sections,
            reviewed_optimization,
            run_output_dir,
            request.company_name,
            run_id,
        )
    else:
        compile_result = await compile_optimized_resume(
            resume_path,
            reviewed_optimization,
            run_output_dir,
            request.company_name,
            run_id,
        )

    if not compile_result["compilation_success"]:
        message = compile_result.get("error", "Compilation failed.")
        log_event(run_id, "REVIEW", f"review application finished with partial status | error={message}")
    else:
        message = ""

    optimized_text = compile_result.get("modified_content", "")
    optimized_score = await score_resume(llm, optimized_text, request.jd_analysis)
    pdf_path = compile_result.get("pdf_path", "")
    tex_path = compile_result.get("tex_path", "")
    log_path = compile_result.get("log_path", "")
    output_dir_path = compile_result.get("output_dir", str(run_output_dir))
    pdf_filename = Path(pdf_path).name if pdf_path else ""
    pdf_relative = _relative_artifact_path(output_root, pdf_path)
    pdf_url = f"/api/download/{pdf_relative}" if pdf_relative else ""
    status = "success" if compile_result["compilation_success"] else "partial"

    log_event(
        run_id,
        "REVIEW",
        f"review changes applied | status={status} final_score={optimized_score.overall_score}/100 pdf={pdf_filename or 'none'}",
    )
    response = OptimizeResponse(
        jd_analysis=request.jd_analysis,
        original_score=request.original_score,
        optimization=reviewed_optimization,
        optimized_score=optimized_score,
        score_roadmap=build_score_roadmap(request.jd_analysis, request.original_score, optimized_score, reviewed_optimization),
        provider=selected_provider,
        model=getattr(llm, "model", None) or "",
        pdf_filename=pdf_filename,
        pdf_url=pdf_url,
        tex_path=_relative_artifact_path(output_root, tex_path),
        pdf_path=pdf_relative,
        log_path=_relative_artifact_path(output_root, log_path),
        output_dir=_relative_artifact_path(output_root, output_dir_path),
        status=status,
        message=message,
        review_applied=True,
    )
    save_history_entry(
        user_id=current_user.id,
        company_name=request.company_name,
        provider=response.provider,
        model=response.model,
        original_score=response.original_score.overall_score,
        optimized_score=response.optimized_score.overall_score,
        status=response.status,
        review_applied=response.review_applied,
        result_payload=response.model_dump(),
    )
    return response


@app.post("/api/upload-template")
async def upload_template(file: UploadFile = File(...), current_user: AuthUser = Depends(get_current_user)):
    """Upload a resume file (PDF or LaTeX .tex)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    filename = file.filename.lower()
    if not (filename.endswith(".pdf") or filename.endswith(".tex")):
        raise HTTPException(status_code=400, detail="File must be a .pdf or .tex file")

    content = await file.read()
    save_path, template_type = save_user_template_bytes(current_user.id, filename, content)
    file_type = "PDF" if template_type == "pdf" else "LaTeX"

    log_event("upload", "TEMPLATE", f"saved {file_type.lower()} template | user={current_user.id} filename={file.filename} bytes={len(content)}")

    return {
        "status": "success",
        "message": f"{file_type} resume '{file.filename}' uploaded successfully",
        "type": file_type.lower(),
    }


@app.post("/api/upload-template-text")
async def upload_template_text(req: TemplateTextRequest, current_user: AuthUser = Depends(get_current_user)):
    """Upload a LaTeX template directly via text payload."""
    save_path = save_user_template_text(current_user.id, req.content)
    log_event("upload", "TEMPLATE", f"saved latex text template | user={current_user.id} chars={len(req.content)} path={save_path}")
    
    return {
        "status": "success",
        "message": "LaTeX template saved successfully",
        "type": "latex",
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


@app.get("/api/download/{file_path:path}")
async def download_pdf(file_path: str, current_user: AuthUser = Depends(get_current_user)):
    """Download a generated PDF file."""
    try:
        resolved_path = resolve_user_output_path(current_user.id, file_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not resolved_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    return FileResponse(
        path=str(resolved_path),
        media_type="application/pdf",
        filename=resolved_path.name,
    )


@app.get("/api/templates")
async def list_templates(current_user: AuthUser = Depends(get_current_user)):
    """List available resume templates."""
    return {"templates": list_user_templates(current_user.id)}
