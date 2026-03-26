"""Ingestion pipeline — loads experience data into ChromaDB (or in-memory fallback)."""
import json
from pathlib import Path

from backend.rag.store import is_available, get_collection, reset_collection

# In-memory fallback store when ChromaDB is unavailable
_memory_store: dict[str, list[dict]] = {
    "experiences": [],
    "skills": [],
    "projects": [],
}


def ingest_experience(data_path: str | Path = "data/experience.json", reset: bool = False) -> int:
    """Ingest experience data from JSON.

    Uses ChromaDB if available, otherwise stores in memory for keyword matching.
    """
    data_path = Path(data_path)
    if not data_path.exists():
        print(f"⚠️  Experience file not found: {data_path}")
        return 0

    with open(data_path) as f:
        data = json.load(f)

    if is_available():
        return _ingest_chromadb(data, reset)
    else:
        return _ingest_memory(data, reset)


def _ingest_memory(data: dict, reset: bool) -> int:
    """Ingest into in-memory store (fallback)."""
    global _memory_store
    if reset:
        _memory_store = {"experiences": [], "skills": [], "projects": []}

    doc_count = 0

    for i, exp in enumerate(data.get("experience", [])):
        exp_id = exp.get("id", f"exp_{i}")
        for j, bullet in enumerate(exp.get("bullets", [])):
            doc = (
                f"{exp.get('title', '')} at {exp.get('company', '')} "
                f"({exp.get('dates', '')}): {bullet}"
            )
            _memory_store["experiences"].append({"id": f"{exp_id}_bullet_{j}", "text": doc})
            doc_count += 1

    for category, skill_list in data.get("skills", {}).items():
        if isinstance(skill_list, list):
            for k, skill in enumerate(skill_list):
                _memory_store["skills"].append({"id": f"skill_{category}_{k}", "text": f"{category}: {skill}"})
                doc_count += 1

    for i, proj in enumerate(data.get("projects", [])):
        proj_id = proj.get("id", f"proj_{i}")
        tech_str = ", ".join(proj.get("tech", []))
        highlights = proj.get("highlights", [])
        doc = (
            f"Project: {proj.get('name', '')} — {proj.get('description', '')} "
            f"Tech: {tech_str}. " + " ".join(highlights)
        )
        _memory_store["projects"].append({"id": proj_id, "text": doc})
        doc_count += 1

    print(f"✅ Ingested {doc_count} documents into memory store (ChromaDB unavailable)")
    return doc_count


def _ingest_chromadb(data: dict, reset: bool) -> int:
    """Ingest into ChromaDB."""
    if reset:
        experiences_col = reset_collection("experiences")
        skills_col = reset_collection("skills")
        projects_col = reset_collection("projects")
    else:
        experiences_col = get_collection("experiences")
        skills_col = get_collection("skills")
        projects_col = get_collection("projects")

    doc_count = 0

    for i, exp in enumerate(data.get("experience", [])):
        exp_id = exp.get("id", f"exp_{i}")
        for j, bullet in enumerate(exp.get("bullets", [])):
            doc_id = f"{exp_id}_bullet_{j}"
            document = (
                f"{exp.get('title', '')} at {exp.get('company', '')} "
                f"({exp.get('dates', '')}): {bullet}"
            )
            metadata = {
                "type": "experience",
                "title": exp.get("title", ""),
                "company": exp.get("company", ""),
                "dates": exp.get("dates", ""),
                "exp_id": exp_id,
            }
            experiences_col.upsert(ids=[doc_id], documents=[document], metadatas=[metadata])
            doc_count += 1

    for category, skill_list in data.get("skills", {}).items():
        if isinstance(skill_list, list):
            for k, skill in enumerate(skill_list):
                doc_id = f"skill_{category}_{k}"
                skills_col.upsert(ids=[doc_id], documents=[f"{category}: {skill}"], metadatas=[{"type": "skill", "category": category}])
                doc_count += 1

    for i, proj in enumerate(data.get("projects", [])):
        proj_id = proj.get("id", f"proj_{i}")
        tech_str = ", ".join(proj.get("tech", []))
        highlights = proj.get("highlights", [])
        document = (
            f"Project: {proj.get('name', '')} — {proj.get('description', '')} "
            f"Tech: {tech_str}. " + " ".join(highlights)
        )
        projects_col.upsert(ids=[proj_id], documents=[document], metadatas=[{"type": "project", "name": proj.get("name", ""), "tech": tech_str, "proj_id": proj_id}])
        doc_count += 1

    print(f"✅ Ingested {doc_count} documents into ChromaDB")
    return doc_count


def get_memory_store() -> dict[str, list[dict]]:
    """Access the in-memory store for keyword-based retrieval."""
    return _memory_store
