# Above WhatsApp University

A browser extension that verifies claims with citations using an **agentic RAG** backend. Highlight any claim on the web, click **Verify claim**, and get a Snopes-style verdict with transparent reasoning and real sources only.

## Features

- **Browser extension (Chrome)**: Right-click on selected text → "Verify claim" → open extension popup (claim pre-filled) → see verdict and citations.
- **Claim classifier (guardrail)**: Pre-retrieval step classifies input as **in scope** (verifiable factual claim) or **out of scope**. Only in-scope claims run retrieval and verification. News headlines and headline-style text (e.g. "What's at stake for…", "Why the Fed raised rates") are always in scope; personal statements, opinions, greetings, and direct questions return "Out of Scope" without retrieval.
- **Agentic RAG**: Decompose → retrieve (ChromaDB + web when Serper/Tavily is set) → optional query rewrite retry → LLM verification with strict citation rules.
- **Richer verdict taxonomy**: True, Mostly True, Mixture, Mostly False, False, Unproven, Out of Scope. Edge cases (conflicting evidence, single weak source, empty retrieval) map to Unproven or Mixture with optional confidence/conflict notes.
- **No fabrication**: Citations come only from retrieved evidence; empty or irrelevant evidence yields "Unproven" and no citations. API and retrieval failures return a safe Unproven response without exposing errors.

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

## Documentation

- **[docs/TECHNICAL.md](docs/TECHNICAL.md)** — Short technical overview (configuration table, pipeline flow, component map).
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — Architecture diagram (RAG + agent flow) and component map.

## Project structure

```
├── extension/           # Chrome extension (Manifest V3)
│   ├── manifest.json
│   ├── background.js    # Context menu "Verify claim"
│   ├── content.js
│   ├── popup.html, popup.js, popup.css
├── backend/
│   ├── main.py          # FastAPI app, POST /verify, GET /health
│   ├── agent/           # Agentic RAG pipeline
│   │   ├── classifier.py # Guardrail: IN_SCOPE / OUT_OF_SCOPE
│   │   ├── pipeline.py  # classify → decompose → retrieve (KB + web) → verify
│   │   ├── retrieval.py # ChromaDB + merge (URL + snippet dedupe)
│   │   ├── web_retrieval.py # Serper/Tavily web search for evidence
│   │   ├── verify.py    # LLM verification, Snopes-style verdicts
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
| `SERPER_API_KEY` | No (for web search) | [Serper](https://serper.dev) API key for real-time web search. If set, evidence is fetched from the web in addition to the KB. |
| `TAVILY_API_KEY` | No (for web search) | [Tavily](https://tavily.com) API key. Used only when `SERPER_API_KEY` is not set. Same role as Serper. |

Without `OPENAI_API_KEY`, the API still runs but returns "Unproven" with a message that verification is not configured; the classifier defaults to in scope so retrieval still runs. Without `SERPER_API_KEY` or `TAVILY_API_KEY`, verification uses only the ChromaDB knowledge base (and returns "Unproven" when no evidence is found).

## Ever-growing knowledge base

- Add more documents to `backend/kb/sample_documents.py` (each with `title`, `url`, `text`), then run `python -m kb.ingest` again to re-index.
- Or implement a separate script that fetches fact-checks (e.g. from RSS or a public dataset), normalizes them to `{title, url, text}`, and calls the same ingest logic so the same `/verify` pipeline stays unchanged.

## Verdict taxonomy and guardrail

- **Verdicts**: True, Mostly True, Mixture, Mostly False, False, Unproven, Out of Scope. The generator uses only the factual set (Out of Scope is set by the guardrail).
- **Guardrail**: The classifier marks as **in scope** factual claims, headlines, and headline-style titles (including "What's at stake…", "Why X", "How Y"). **Out of scope**: personal statements, pure opinions, direct questions for information, greetings, advice requests, or too vague/nonsensical. When in doubt the classifier prefers in scope.
- **Edge cases**: Empty retrieval → Unproven (no LLM call). Conflicting evidence → Mixture or Unproven with conflict noted. Single weak source → Unproven or Mostly True/Mostly False with a confidence note. Input length is capped; API/key failures return Unproven without stack traces.

## API

- **POST /verify**  
  Body: `{"claim": "user-selected or pasted text"}` (max length enforced).  
  Response: `{"verdict", "verdict_category", "reasoning", "citations": [{"title", "url", "snippet"}], "evidence_count", "conflict_mentioned", "confidence_note"}`.  
  Verdict is one of: True, Mostly True, Mixture, Mostly False, False, Unproven, Out of Scope.

- **GET /health**  
  Returns `{"status": "ok", "web_search_configured": true|false}`.

## Constraints

- **Never fabricate**: Citations are built only from retrieval/search results; the LLM may only reference provided source indices.
- **Empty evidence**: No generator call; response is Unproven with empty citations.
- **Safety**: Input length limits; on retrieval or LLM failure the API returns Unproven with a short message and never exposes stack traces.

### Real-time web verification

To have the backend **proactively fetch evidence from the web** (so the user only submits a headline or claim):

1. Get an API key from [Serper](https://serper.dev) or [Tavily](https://tavily.com).
2. Set one of: `export SERPER_API_KEY=...` or `export TAVILY_API_KEY=...` (Serper is tried first).
3. Restart the backend. The pipeline will then query the web for each claim (and decomposed/rewritten queries), merge results with ChromaDB, and pass the combined evidence to the verification LLM. Citations will include both KB and web sources; no user-supplied evidence is required.
