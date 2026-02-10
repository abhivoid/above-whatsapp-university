# Real-Time News Claim Verification Assistant

A browser extension that verifies claims with citations using an **agentic RAG** backend. Highlight any claim on the web, click **Verify claim**, and get a verdict (Supported / Refuted / Not Enough Evidence) with transparent reasoning and real sources only.

## Features

- **Browser extension (Chrome)**: Right-click on selected text → "Verify claim" → open extension popup (claim pre-filled) → see verdict and citations.
- **Agentic RAG**: Claim decomposition, retrieval from a vector knowledge base, optional query rewrite and second retrieval, then LLM verification with strict citation rules.
- **No fabrication**: Citations come only from retrieved evidence; if there is not enough evidence, the system returns "Not Enough Evidence" and no citations.

## Quick start

### 1. Backend (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Set your OpenAI API key (required for verification and agentic steps):

```bash
export OPENAI_API_KEY=sk-...
# Optional: OPENAI_MODEL=gpt-4o-mini
```

Seed the knowledge base (run once):

```bash
python -m kb.ingest
```

Start the API:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The `/verify` endpoint will be at `http://localhost:8000/verify`.

### 2. Chrome extension

1. Open Chrome → **Extensions** → **Manage extensions** → **Load unpacked**.
2. Select the `extension` folder from this repo.
3. Use the extension:
   - **From selection**: Highlight text on any page → right-click → **Verify claim**. Then click the extension icon; the popup will open with the claim pre-filled. Click **Verify claim** to run verification.
   - **From popup**: Click the extension icon, paste or type a claim, then click **Verify claim**.

The popup shows verdict, reasoning, and clickable citations (title + snippet). Citation links open in a new tab.

### 3. Demo flow

1. Start the backend and run `python -m kb.ingest` once.
2. Load the extension and open any webpage.
3. Highlight a claim (e.g. "COVID-19 vaccines contain microchips" or "5G causes COVID-19").
4. Right-click → **Verify claim**, then click the extension icon.
5. In the popup, click **Verify claim** and see the verdict with citations.

## Project structure

```
├── extension/           # Chrome extension (Manifest V3)
│   ├── manifest.json
│   ├── background.js    # Context menu "Verify claim"
│   ├── content.js
│   ├── popup.html, popup.js, popup.css
├── backend/
│   ├── main.py          # FastAPI app, POST /verify
│   ├── agent/           # Agentic RAG pipeline
│   │   ├── pipeline.py  # decompose → retrieve → verify
│   │   ├── retrieval.py # ChromaDB + merge
│   │   ├── verify.py    # LLM verification, citation parsing
│   │   ├── prompts.py
│   │   └── llm_helpers.py # decompose, query rewrite
│   ├── kb/
│   │   ├── ingest.py    # Embed and index documents
│   │   └── sample_documents.py # Seed fact-check style docs
│   └── requirements.txt
└── README.md
```

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes (for verification) | OpenAI API key for LLM calls. |
| `OPENAI_MODEL` | No | Model name (default: `gpt-4o-mini`). |
| `CHROMA_PERSIST_DIR` | No | Path for ChromaDB data (default: `backend/chroma_data`). |

Without `OPENAI_API_KEY`, the API still runs but returns "Not Enough Evidence" with a message that verification is not configured.

## Ever-growing knowledge base

- Add more documents to `backend/kb/sample_documents.py` (each with `title`, `url`, `text`), then run `python -m kb.ingest` again to re-index.
- Or implement a separate script that fetches fact-checks (e.g. from RSS or a public dataset), normalizes them to `{title, url, text}`, and calls the same ingest logic so the same `/verify` pipeline stays unchanged.

## Constraints (as per challenge)

- **Always cite sources**: Supported/Refuted answers include at least one citation from the knowledge base (or future web search).
- **Never fabricate**: Citations are built only from retrieval/search results; the LLM may only reference provided source indices.
- **Not Enough Evidence**: When retrieval returns nothing or the LLM decides evidence is insufficient, the verdict is "Not Enough Evidence" and the citations list is empty.

## API

- **POST /verify**  
  Body: `{"claim": "user-selected or pasted text"}`  
  Response: `{"verdict": "Supported|Refuted|Not Enough Evidence", "reasoning": "...", "citations": [{"title", "url", "snippet"}]}`

- **GET /health**  
  Returns `{"status": "ok"}`.
