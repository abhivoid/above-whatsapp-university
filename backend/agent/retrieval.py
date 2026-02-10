"""
Retrieval from vector store (ChromaDB). Returns list of {title, url, snippet}.
"""
import os
from pathlib import Path

# Lazy init to avoid import errors when chroma not yet set up
_chroma_client = None
_collection = None
_embedding_fn = None


def _get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_fn = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            raise RuntimeError(f"Failed to load embedding model: {e}") from e
    return _embedding_fn


def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        try:
            import chromadb
            from chromadb.config import Settings
            persist_dir = os.environ.get("CHROMA_PERSIST_DIR", str(Path(__file__).resolve().parents[1] / "chroma_data"))
            Path(persist_dir).mkdir(parents=True, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(path=persist_dir, settings=Settings(anonymized_telemetry=False))
            _collection = _chroma_client.get_or_create_collection(
                name="claim_evidence",
                metadata={"description": "Evidence chunks for claim verification"},
            )
        except Exception as e:
            raise RuntimeError(f"Failed to init ChromaDB: {e}") from e
    return _collection


def retrieve_evidence(claim: str, max_chunks: int = 10) -> list[dict]:
    """
    Embed claim, query vector store, return list of {title, url, snippet}.
    Returns [] if collection is empty or query fails.
    """
    try:
        collection = _get_collection()
        n = collection.count()
        if n == 0:
            return []
        model = _get_embedding_fn()
        embedding = model.encode([claim], normalize_embeddings=True).tolist()[0]
        results = collection.query(
            query_embeddings=[embedding],
            n_results=min(max_chunks, n),
            include=["metadatas", "documents"],
        )
    except Exception:
        return []

    if not results or not results["ids"] or not results["ids"][0]:
        return []

    out = []
    for i, doc_id in enumerate(results["ids"][0]):
        metadatas = (results.get("metadatas") or [[]])[0]
        docs = (results.get("documents") or [[]])[0]
        meta = metadatas[i] if i < len(metadatas) else {}
        doc = docs[i] if i < len(docs) else ""
        out.append({
            "title": meta.get("title", "Unknown"),
            "url": meta.get("url", ""),
            "snippet": (doc or "")[:500],
        })
    return out


def merge_evidence(evidence_lists: list[list[dict]]) -> list[dict]:
    """Merge multiple evidence lists and deduplicate by url. Order preserved (first occurrence kept)."""
    seen_urls: set[str] = set()
    out: list[dict] = []
    for lst in evidence_lists:
        for e in lst:
            url = (e.get("url") or "").strip()
            if url and url not in seen_urls:
                seen_urls.add(url)
                out.append(e)
            elif not url and e not in out:
                out.append(e)
    return out
