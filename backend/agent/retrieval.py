"""
Retrieval from vector store (ChromaDB). Returns list of {title, url, snippet}.
"""
import os
import warnings
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

# Lazy init to avoid import errors when chroma not yet set up
_chroma_client = None
_collection = None
_embedding_fn = None


def _get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is None:
        try:
            # Suppress harmless warnings from sentence-transformers model loading
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning)
                os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
                from sentence_transformers import SentenceTransformer
                # Suppress transformers library stderr output during model loading
                with redirect_stderr(StringIO()):
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


def _snippet_fingerprint(snippet: str, length: int = 120) -> str:
    """Normalize snippet for similarity dedupe: strip, lowercase, truncate."""
    s = (snippet or "").strip().lower()[:length]
    return " ".join(s.split())


def merge_evidence(
    evidence_lists: list[list[dict]],
    dedupe_by_snippet: bool = True,
    snippet_dedupe_len: int = 120,
) -> list[dict]:
    """
    Merge multiple evidence lists. Deduplicate by URL (always); optionally by snippet fingerprint.
    Order preserved (first occurrence kept). Near-duplicate snippets (same fingerprint) are dropped.
    """
    seen_urls: set[str] = set()
    seen_fingerprints: set[str] = set()
    out: list[dict] = []
    for lst in evidence_lists:
        for e in lst:
            url = (e.get("url") or "").strip()
            snippet = e.get("snippet") or ""
            fp = _snippet_fingerprint(snippet, snippet_dedupe_len) if dedupe_by_snippet else ""
            if url and url in seen_urls:
                continue
            if dedupe_by_snippet and fp and fp in seen_fingerprints:
                continue
            if url:
                seen_urls.add(url)
            if fp:
                seen_fingerprints.add(fp)
            out.append(e)
    return out
