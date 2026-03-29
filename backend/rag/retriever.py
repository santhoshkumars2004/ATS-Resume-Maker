"""RAG retriever — queries ChromaDB or in-memory store for relevant experience."""
from backend.models import JDAnalysis
from backend.logging_utils import log_event
from backend.rag.store import is_available, get_collection


async def retrieve_relevant_experience(
    jd_analysis: JDAnalysis,
    top_k: int = 5,
    run_id: str | None = None,
) -> str:
    """Retrieve the most relevant experience for a given job description.

    Uses ChromaDB if available, otherwise falls back to keyword matching.
    """
    mode = "chromadb" if is_available() else "memory"
    if run_id:
        log_event(run_id, "RAG", f"starting retrieval | mode={mode} top_k={top_k}")

    result = _retrieve_chromadb(jd_analysis, top_k) if is_available() else _retrieve_memory(jd_analysis, top_k)

    if run_id:
        snippet_count = result.count("•")
        if result:
            log_event(run_id, "RAG", f"retrieved {snippet_count} relevant snippets")
        else:
            log_event(run_id, "RAG", "no relevant experience matched the job description")

    return result


def _retrieve_chromadb(jd_analysis: JDAnalysis, top_k: int) -> str:
    """Retrieve using ChromaDB vector search."""
    query_parts = []
    if jd_analysis.required_skills:
        query_parts.append(f"Skills: {', '.join(jd_analysis.required_skills)}")
    if jd_analysis.keywords:
        query_parts.append(f"Keywords: {', '.join(jd_analysis.keywords)}")
    if jd_analysis.responsibilities:
        query_parts.append(f"Responsibilities: {', '.join(jd_analysis.responsibilities[:3])}")

    query_text = ". ".join(query_parts)
    if not query_text:
        return ""

    results = []

    for collection_name in ["experiences", "projects"]:
        try:
            collection = get_collection(collection_name)
            if collection and collection.count() > 0:
                r = collection.query(
                    query_texts=[query_text],
                    n_results=min(top_k, collection.count()),
                )
                if r and r["documents"]:
                    for doc in r["documents"][0]:
                        results.append(f"• {doc}")
        except Exception:
            pass

    if not results:
        return ""

    return "Relevant experience from knowledge base:\n" + "\n".join(results)


def _retrieve_memory(jd_analysis: JDAnalysis, top_k: int) -> str:
    """Retrieve using simple keyword matching (fallback)."""
    from backend.rag.ingest import get_memory_store

    store = get_memory_store()
    if not store["experiences"] and not store["projects"]:
        return ""

    # Build keyword set from JD
    keywords = set()
    for skill in jd_analysis.required_skills + jd_analysis.preferred_skills:
        keywords.add(skill.lower())
    for kw in jd_analysis.keywords:
        keywords.add(kw.lower())
    for tech in jd_analysis.tech_stack:
        keywords.add(tech.lower())

    if not keywords:
        return ""

    # Score documents by keyword overlap
    scored = []
    for doc in store["experiences"] + store["projects"]:
        text_lower = doc["text"].lower()
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scored.append((score, doc["text"]))

    scored.sort(reverse=True)
    top_results = scored[:top_k]

    if not top_results:
        return ""

    results = [f"• {text}" for _, text in top_results]
    return "Relevant experience from knowledge base:\n" + "\n".join(results)
