"""
Ingest documents into the claim verification vector store (ChromaDB).
Run from backend directory: python -m kb.ingest
Uses the same embedding model and collection as agent.retrieval.
"""
import sys
from pathlib import Path

# Run from repo root or backend; ensure backend is on path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

from kb.sample_documents import SAMPLE_DOCUMENTS

CHUNK_SIZE = 400
COLLECTION_NAME = "claim_evidence"
PERSIST_DIR = backend_dir / "chroma_data"


def chunk_text(text: str, size: int = CHUNK_SIZE) -> list[str]:
    """Split text into overlapping chunks for embedding."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end]
        # Prefer breaking at sentence end
        for sep in ".!?\n":
            last = chunk.rfind(sep)
            if last > size // 2:
                chunk = chunk[: last + 1]
                end = start + len(chunk)
                break
        chunks.append(chunk.strip())
        start = end
        if start < len(text) and not text[start].isspace():
            start = max(0, start - 50)  # Slight overlap
    return chunks


def main():
    persist_dir = str(PERSIST_DIR)
    PERSIST_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print("Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=persist_dir, settings=Settings(anonymized_telemetry=False))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Evidence chunks for claim verification"},
    )

    ids = []
    documents = []
    metadatas = []

    for i, doc in enumerate(SAMPLE_DOCUMENTS):
        title = doc.get("title", "Unknown")
        url = doc.get("url", "")
        text = doc.get("text", "")
        if not text:
            continue
        chunks = chunk_text(text)
        for j, chunk in enumerate(chunks):
            doc_id = f"doc_{i}_chunk_{j}"
            ids.append(doc_id)
            documents.append(chunk)
            metadatas.append({"title": title, "url": url})

    if not ids:
        print("No documents to add.")
        return

    print(f"Embedding {len(ids)} chunks...")
    embeddings = model.encode(documents, normalize_embeddings=True).tolist()

    # ChromaDB expects list of lists for add
    collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    print(f"Added {len(ids)} chunks from {len(SAMPLE_DOCUMENTS)} documents to collection '{COLLECTION_NAME}'.")
    print(f"Persist directory: {persist_dir}")


if __name__ == "__main__":
    main()
